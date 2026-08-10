from __future__ import annotations

import io
import json
import logging
import platform
import queue
import secrets
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

import qrcode
import soundfile as sf
from PySide6.QtCore import QSize, QSettings, QStandardPaths, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QToolButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .audio_engine import AudioEngine
from .controller_server import ControllerServer
from .logging_setup import configure_logging, install_exception_hook
from .power import PowerInhibitor
from .session import ProjectSession, TakeMetadata
from .theme import APP_STYLESHEET
from .utils import advance_take_number, format_duration, resource_path
from .ui_icons import brand_icon, brand_pixmap, make_icon
from .version import APP_NAME, APP_VERSION, ORGANIZATION_NAME
from .widgets import Card, DeviceComboBox, StatusPill, TrackRow, TransportButton, TransportControl

LOGGER = logging.getLogger("filmsetrecorder.ui")


def _local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _default_project_dir() -> Path:
    documents = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
    root = Path(documents) if documents else Path.home() / "Documents"
    return root / "FilmSet Recorder" / "Untitled Project"


def _ui_icon(name: str) -> QIcon:
    """Return a vector-rendered product icon.

    UI icons are generated in Qt at runtime so a packaging/layout change can
    never make the controls silently lose their graphics.
    """
    return make_icon(name, 64)


def _icon_label(name: str, size: int = 20) -> QLabel:
    label = QLabel()
    label.setObjectName("SectionIcon")
    label.setFixedSize(size + 4, size + 4)
    label.setAlignment(Qt.AlignCenter)
    icon = _ui_icon(name)
    if not icon.isNull():
        label.setPixmap(icon.pixmap(QSize(size, size)))
    return label


def _button_icon(button: QPushButton, name: str, size: int = 18) -> None:
    icon = _ui_icon(name)
    if not icon.isNull():
        button.setIcon(icon)
        button.setIconSize(QSize(size, size))


class MainWindow(QMainWindow):
    MAX_TRACK_ROWS = 16
    MIN_RECORD_FREE_BYTES = 512 * 1024 * 1024
    EMERGENCY_STOP_FREE_BYTES = 256 * 1024 * 1024

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(820, 620)
        self.resize(1280, 800)

        self.settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        self.meter_queue: queue.Queue[tuple[list[float], list[float]]] = queue.Queue(maxsize=8)
        self.remote_commands: queue.Queue[dict] = queue.Queue(maxsize=64)
        self._remote_state_lock = threading.Lock()
        self._remote_state_cache: dict = {}
        self.last_meter_values: list[float] = [-80.0] * 4
        self.last_rms_values: list[float] = [-80.0] * 4

        self.audio = AudioEngine(meter_callback=self._meter_from_audio_thread)
        self.power_inhibitor = PowerInhibitor()
        project_value = str(self.settings.value("project/path", str(_default_project_dir())))
        self.session = ProjectSession(Path(project_value))

        self.last_take_path: Path | None = None
        self.current_take_path: Path | None = None
        self.current_take_snapshot: dict | None = None
        self.circle_take = False
        self._circle_targets_last = False
        self._writer_error_seen: str | None = None
        self._last_disk_update = 0
        self._devices_cache = []
        self._selected_device_max_inputs = 1
        self._emergency_stop_triggered = False
        self._emergency_stop_reason: str | None = None
        self._last_xrun_seen = 0

        token = str(self.settings.value("remote/token", "")).strip()
        if len(token) < 4:
            token = f"{secrets.randbelow(1_000_000):06d}"
            self.settings.setValue("remote/token", token)
        self.remote_token = token
        self.remote_address = ""

        self._build_menu()
        self._build_ui()
        self._restore_ui_state()
        self._load_devices()
        self.refresh_take_browser()
        self._install_shortcuts()
        self._start_remote_server()

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._tick)
        self.ui_timer.start(40)

        QTimer.singleShot(600, self._check_recovery)
        LOGGER.info("Application window initialized")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        choose_action = QAction("Choose Project Folder...", self)
        choose_action.triggered.connect(self.choose_project)
        file_menu.addAction(choose_action)

        open_action = QAction("Open Project Folder", self)
        open_action.triggered.connect(self.open_project_folder)
        file_menu.addAction(open_action)

        report_action = QAction("Open Sound Report", self)
        report_action.triggered.connect(self.open_sound_report)
        file_menu.addAction(report_action)
        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = self.menuBar().addMenu("Tools")
        audio_setup_action = QAction("Audio Setup...", self)
        audio_setup_action.triggered.connect(lambda: self.workspace.setCurrentIndex(4))
        tools_menu.addAction(audio_setup_action)
        tools_menu.addSeparator()
        diagnostics_action = QAction("Save Diagnostics...", self)
        diagnostics_action.triggered.connect(self.save_diagnostics)
        tools_menu.addAction(diagnostics_action)

        reset_peaks_action = QAction("Reset Meter Peaks", self)
        reset_peaks_action.triggered.connect(self.reset_meter_peaks)
        tools_menu.addAction(reset_peaks_action)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About FilmSet Recorder", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        """Build the v0.6.5 production-console interface.

        This layout intentionally follows the approved visual mockup: branded
        rail navigation, a compact production header, a large slate, calibrated
        ISO meters, dedicated recorder telemetry, circular transport controls,
        and a persistent last-take/history/notes strip.
        """
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        # LEFT NAV ---------------------------------------------------------
        nav = QWidget()
        nav.setObjectName("NavRail")
        nav.setFixedWidth(88)
        nav_l = QVBoxLayout(nav)
        nav_l.setContentsMargins(8, 14, 8, 12)
        nav_l.setSpacing(8)
        logo = QLabel()
        logo.setObjectName("LogoMark")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(54)
        logo.setPixmap(brand_pixmap(42))
        nav_l.addWidget(logo)
        self.nav_buttons = []

        def nav_button(text: str, icon_name: str, index: int):
            btn = QToolButton()
            btn.setText(text)
            btn.setIcon(_ui_icon(icon_name))
            btn.setIconSize(QSize(25, 25))
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setMinimumHeight(66)
            btn.clicked.connect(lambda _checked=False, i=index: self.workspace.setCurrentIndex(i))
            nav_l.addWidget(btn)
            self.nav_buttons.append(btn)
            return btn

        nav_button("Record", "record", 0)
        nav_button("Takes", "takes", 1)
        nav_button("Notes", "notes", 2)
        nav_button("Remote", "remote", 3)
        nav_button("System", "system", 4)
        self.nav_buttons[0].setChecked(True)
        nav_l.addStretch(1)
        help_button = QToolButton()
        help_button.setText("Help")
        help_button.setIcon(_ui_icon("help"))
        help_button.setIconSize(QSize(22, 22))
        help_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        help_button.setObjectName("NavHelpButton")
        help_button.clicked.connect(self.show_about)
        nav_l.addWidget(help_button)
        shell.addWidget(nav)

        # APPLICATION BODY -------------------------------------------------
        body = QWidget()
        body.setObjectName("AppBody")
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(16, 10, 16, 8)
        body_l.setSpacing(9)
        shell.addWidget(body, 1)

        # BRAND / STATUS BAR -- follows the approved mockup hierarchy.
        top = QHBoxLayout()
        top.setSpacing(10)
        brand_icon_label = QLabel()
        brand_icon_label.setObjectName("BrandWave")
        brand_icon_label.setFixedSize(48, 48)
        brand_icon_label.setAlignment(Qt.AlignCenter)
        brand_icon_label.setPixmap(brand_pixmap(44))
        top.addWidget(brand_icon_label)

        product = QVBoxLayout()
        product.setSpacing(-1)
        product_name = QLabel("F I L M S E T")
        product_name.setObjectName("ProductName")
        product_sub = QLabel("R E C O R D E R")
        product_sub.setObjectName("ProductSub")
        product.addWidget(product_name)
        product.addWidget(product_sub)
        top.addLayout(product)

        divider = QFrame()
        divider.setObjectName("HeaderDivider")
        divider.setFrameShape(QFrame.VLine)
        divider.setFixedHeight(42)
        top.addWidget(divider)

        project = QVBoxLayout()
        project.setSpacing(0)
        self.project_title = QLabel(self.session.project_name)
        self.project_title.setObjectName("ProjectTitle")
        self.project_subtitle = QLabel("ACTIVE PROJECT")
        self.project_subtitle.setObjectName("AppSubtitle")
        project.addWidget(self.project_title)
        project.addWidget(self.project_subtitle)
        top.addLayout(project)
        top.addStretch(1)

        self.format_label = QLabel("48 kHz · 24-bit · POLY WAV")
        self.format_label.setObjectName("FormatReadout")
        top.addWidget(self.format_label)
        self.audio_pill = StatusPill("AUDIO OFF", "neutral", _ui_icon("audio"), "Select interface")
        self.remote_pill = StatusPill("REMOTE", "neutral", _ui_icon("remote"), "Starting…")
        self.disk_pill = StatusPill("DISK", "neutral", _ui_icon("disk"), "--")
        self.state_pill = StatusPill("IDLE", "neutral", _ui_icon("idle"), "")
        for pill in (self.audio_pill, self.remote_pill, self.disk_pill, self.state_pill):
            top.addWidget(pill)
        system_shortcut = QToolButton()
        system_shortcut.setObjectName("HeaderToolButton")
        system_shortcut.setIcon(_ui_icon("system"))
        system_shortcut.setIconSize(QSize(24, 24))
        system_shortcut.setToolTip("Open System & Audio Setup")
        system_shortcut.clicked.connect(lambda: self.workspace.setCurrentIndex(4))
        top.addWidget(system_shortcut)
        body_l.addLayout(top)

        self.workspace = QTabWidget()
        self.workspace.setObjectName("WorkspaceTabs")
        self.workspace.tabBar().hide()
        body_l.addWidget(self.workspace, 1)

        # RECORD WORKSPACE =================================================
        record_page = QWidget()
        record_page.setObjectName("RecordWorkspace")
        record_l = QVBoxLayout(record_page)
        record_l.setContentsMargins(0, 0, 0, 0)
        record_l.setSpacing(9)

        # Slate ------------------------------------------------------------
        slate = QFrame()
        slate.setObjectName("SlatePanel")
        sg = QGridLayout(slate)
        sg.setContentsMargins(18, 12, 18, 13)
        sg.setHorizontalSpacing(14)
        sg.setVerticalSpacing(3)
        sg.addWidget(_icon_label("slate", 21), 0, 0)
        slate_title = QLabel("SLATE")
        slate_title.setObjectName("SectionTitle")
        sg.addWidget(slate_title, 0, 1, 1, 3)

        self.roll_edit = QLineEdit("A001")
        self.scene_edit = QLineEdit("1")
        self.take_spin = QSpinBox()
        self.take_spin.setRange(1, 99999)
        self.take_spin.setValue(1)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["23.976", "24", "25", "29.97", "30"])
        slate_fields = (("ROLL", self.roll_edit), ("SCENE", self.scene_edit), ("TAKE", self.take_spin), ("FRAMERATE", self.fps_combo))
        for col, (title, widget) in enumerate(slate_fields):
            lab = QLabel(title)
            lab.setObjectName("FieldLabel")
            sg.addWidget(lab, 1, col)
            widget.setObjectName("SlateField")
            widget.setMinimumHeight(50)
            sg.addWidget(widget, 2, col)

        file_wrap = QFrame()
        file_wrap.setObjectName("NextFileField")
        file_l = QHBoxLayout(file_wrap)
        file_l.setContentsMargins(10, 5, 10, 5)
        file_l.setSpacing(8)
        file_l.addWidget(_icon_label("report", 19))
        self.filename_preview = QLabel("")
        self.filename_preview.setObjectName("FilePreview")
        self.filename_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        file_l.addWidget(self.filename_preview, 1)
        next_label = QLabel("NEXT FILE")
        next_label.setObjectName("FieldLabel")
        sg.addWidget(next_label, 1, 4)
        sg.addWidget(file_wrap, 2, 4)

        reset_take = QPushButton("Reset Take")
        reset_take.setObjectName("SlateResetButton")
        _button_icon(reset_take, "reset")
        reset_take.clicked.connect(lambda: self.take_spin.setValue(1))
        sg.addWidget(reset_take, 2, 5)
        for c in range(6):
            sg.setColumnStretch(c, 1 if c < 4 else (2 if c == 4 else 0))
        record_l.addWidget(slate)

        # Meter console + recorder ----------------------------------------
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)
        record_l.addWidget(self.main_splitter, 1)

        console = QFrame()
        console.setObjectName("MeterConsole")
        cl = QVBoxLayout(console)
        cl.setContentsMargins(14, 11, 14, 10)
        cl.setSpacing(5)
        ch = QHBoxLayout()
        title = QLabel("ISO TRACKS")
        title.setObjectName("SectionTitle")
        self.input_summary = QLabel("1 INPUT · 24-bit / 48 kHz")
        self.input_summary.setObjectName("SectionMeta")
        ch.addWidget(_icon_label("tracks", 21))
        ch.addWidget(title)
        ch.addStretch(1)
        ch.addWidget(self.input_summary)
        cl.addLayout(ch)

        self.track_scroll = QScrollArea()
        self.track_scroll.setWidgetResizable(True)
        self.track_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        track_container = QWidget()
        track_container.setObjectName("TrackContainer")
        self.track_layout = QVBoxLayout(track_container)
        self.track_layout.setContentsMargins(0, 0, 0, 0)
        self.track_layout.setSpacing(3)
        self.track_rows = []
        default_names = ["BOOM", "LAV A", "LAV B", "PLANT"]
        for index in range(self.MAX_TRACK_ROWS):
            row = TrackRow(index, default_names[index] if index < 4 else f"INPUT {index + 1}")
            row.armedChanged.connect(self._track_arm_changed)
            self.track_rows.append(row)
            self.track_layout.addWidget(row)
            row.setVisible(index < 4)

        self.add_input_btn = QPushButton("ADD INPUT")
        self.add_input_btn.setObjectName("AddInputButton")
        _button_icon(self.add_input_btn, "plus", 16)
        self.add_input_btn.setToolTip("Add the next available hardware input to the recording layout.")
        self.add_input_btn.clicked.connect(self._add_input_track)
        self.track_layout.addWidget(self.add_input_btn, 0, Qt.AlignLeft)
        self.track_layout.addStretch(1)
        self.track_scroll.setWidget(track_container)
        cl.addWidget(self.track_scroll, 1)
        self.main_splitter.addWidget(console)

        recorder = QFrame()
        recorder.setObjectName("RecorderPanel")
        rl = QVBoxLayout(recorder)
        rl.setContentsMargins(16, 13, 16, 13)
        rl.setSpacing(8)
        rh = QHBoxLayout()
        rh.addWidget(_icon_label("record", 15))
        rt = QLabel("RECORDER")
        rt.setObjectName("SectionTitle")
        rh.addWidget(rt)
        rh.addStretch(1)
        self.quick_audio_state = QLabel("AUDIO OFF")
        self.quick_audio_state.setObjectName("TinyState")
        rh.addWidget(self.quick_audio_state)
        rl.addLayout(rh)

        clock_box = QFrame()
        clock_box.setObjectName("ClockPanel")
        clock_l = QVBoxLayout(clock_box)
        clock_l.setContentsMargins(8, 12, 8, 10)
        clock_l.setSpacing(2)
        self.clock = QLabel("00:00:00:00")
        self.clock.setObjectName("HeroClock")
        self.clock.setAlignment(Qt.AlignCenter)
        clock_l.addWidget(self.clock)
        clock_labels = QHBoxLayout()
        for label in ("HOURS", "MINUTES", "SECONDS", "FRAMES"):
            lab = QLabel(label)
            lab.setObjectName("ClockUnit")
            lab.setAlignment(Qt.AlignCenter)
            clock_labels.addWidget(lab, 1)
        clock_l.addLayout(clock_labels)
        self.transport_slate = QLabel("A001 · SC 1 · T001")
        self.transport_slate.setObjectName("TransportSlate")
        self.transport_slate.setAlignment(Qt.AlignCenter)
        clock_l.addWidget(self.transport_slate)
        self.recorder_state_badge = QLabel("IDLE")
        self.recorder_state_badge.setObjectName("RecorderStateBadge")
        self.recorder_state_badge.setProperty("tone", "idle")
        self.recorder_state_badge.setAlignment(Qt.AlignCenter)
        clock_l.addWidget(self.recorder_state_badge, 0, Qt.AlignCenter)
        rl.addWidget(clock_box)

        health_frame = QFrame()
        health_frame.setObjectName("RecorderHealth")
        hg = QGridLayout(health_frame)
        hg.setContentsMargins(4, 7, 4, 7)
        hg.setHorizontalSpacing(0)
        self.quick_preroll = QLabel("5 sec")
        self.quick_buffer = QLabel("512")
        self.quick_inputs = QLabel("1 / 1")
        for col, (name, value) in enumerate((("Pre-Roll", self.quick_preroll), ("Buffered", self.quick_buffer), ("Inputs", self.quick_inputs))):
            dot = QLabel("●")
            dot.setObjectName("HealthDot")
            dot.setAlignment(Qt.AlignCenter)
            name_label = QLabel(name)
            name_label.setObjectName("HealthLabel")
            name_label.setAlignment(Qt.AlignCenter)
            value.setObjectName("HealthValue")
            value.setAlignment(Qt.AlignCenter)
            top_row = QHBoxLayout()
            top_row.setSpacing(3)
            top_row.addStretch(1)
            top_row.addWidget(dot)
            top_row.addWidget(name_label)
            top_row.addStretch(1)
            cell = QWidget()
            cell_l = QVBoxLayout(cell)
            cell_l.setContentsMargins(3, 0, 3, 0)
            cell_l.setSpacing(0)
            cell_l.addLayout(top_row)
            cell_l.addWidget(value)
            hg.addWidget(cell, 0, col)
        rl.addWidget(health_frame)

        qlab = QLabel("INPUT DEVICE")
        qlab.setObjectName("FieldLabel")
        rl.addWidget(qlab)
        quick_device = QHBoxLayout()
        self.input_combo = DeviceComboBox()
        self.input_combo.setObjectName("InputDeviceCombo")
        self.input_combo.setMinimumHeight(38)
        quick_device.addWidget(self.input_combo, 1)
        self.apply_audio_button = QPushButton("Apply")
        _button_icon(self.apply_audio_button, "play", 15)
        self.apply_audio_button.setObjectName("QuickApplyButton")
        self.apply_audio_button.setProperty("role", "primary")
        self.apply_audio_button.clicked.connect(self.apply_audio)
        quick_device.addWidget(self.apply_audio_button)
        rl.addLayout(quick_device)
        self.device_hint = QLabel("Select the interface carrying production microphones.")
        self.device_hint.setObjectName("AppSubtitle")
        self.device_hint.setWordWrap(True)
        rl.addWidget(self.device_hint)
        self.awake_check = QCheckBox("Keep computer awake")
        self.awake_check.toggled.connect(self._set_power_mode)
        rl.addWidget(self.awake_check)
        rl.addStretch(1)
        self.main_splitter.addWidget(recorder)
        self.main_splitter.setStretchFactor(0, 5)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([900, 350])

        # Circular transport deck -----------------------------------------
        transport = QFrame()
        transport.setObjectName("TransportDeck")
        tl = QHBoxLayout(transport)
        tl.setContentsMargins(22, 8, 22, 8)
        tl.setSpacing(12)

        self.record_control = TransportControl("RECORD", _ui_icon("record"), "record", "F9")
        self.record_btn = self.record_control.button
        self.record_btn.clicked.connect(self.toggle_record)
        self.stop_control = TransportControl("STOP", _ui_icon("stop"), "stop", "ESC")
        self.stop_btn = self.stop_control.button
        self.stop_btn.clicked.connect(self.stop_all)
        self.play_control = TransportControl("PLAY LAST", _ui_icon("play"), "secondary", "F8")
        self.play_btn = self.play_control.button
        self.play_btn.clicked.connect(self.play_last)
        self.next_control = TransportControl("NEXT TAKE", _ui_icon("next"), "secondary", "CTRL+N")
        self.next_btn = self.next_control.button
        self.next_btn.clicked.connect(self.next_take)
        self.circle_control = TransportControl("CIRCLE", _ui_icon("circle"), "circle", "C")
        self.circle_btn = self.circle_control.button
        self.circle_btn.setCheckable(True)
        self.circle_btn.clicked.connect(self.set_circle)
        self.circle_btn.setToolTip("Mark the current or last completed take as preferred for editorial. Audio is unchanged.")

        controls = (self.record_control, self.stop_control, self.play_control, self.next_control, self.circle_control)
        for idx, control in enumerate(controls):
            tl.addWidget(control, 1)
            if idx < len(controls) - 1:
                sep = QFrame()
                sep.setObjectName("TransportDivider")
                sep.setFrameShape(QFrame.VLine)
                sep.setFixedHeight(58)
                tl.addWidget(sep)
        record_l.addWidget(transport)

        # Production strip: Last Take / history / current notes -----------
        production_strip = QFrame()
        production_strip.setObjectName("ProductionStrip")
        ps = QHBoxLayout(production_strip)
        ps.setContentsMargins(12, 9, 12, 9)
        ps.setSpacing(12)

        last_panel = QWidget()
        last_l = QVBoxLayout(last_panel)
        last_l.setContentsMargins(0, 0, 0, 0)
        last_l.setSpacing(3)
        lth = QLabel("LAST TAKE")
        lth.setObjectName("StripTitle")
        last_l.addWidget(lth)
        last_row = QHBoxLayout()
        self.last_take_icon = QLabel()
        self.last_take_icon.setFixedSize(40, 40)
        self.last_take_icon.setPixmap(_ui_icon("waveform").pixmap(QSize(28, 28)))
        self.last_take_icon.setAlignment(Qt.AlignCenter)
        self.last_take_icon.setObjectName("LastTakeIcon")
        last_row.addWidget(self.last_take_icon)
        last_text = QVBoxLayout()
        self.last_take_name = QLabel("No completed take")
        self.last_take_name.setObjectName("LastTakeName")
        self.last_take_meta = QLabel("—")
        self.last_take_meta.setObjectName("LastTakeMeta")
        self.last_take_note = QLabel("")
        self.last_take_note.setObjectName("LastTakeNote")
        self.last_take_note.setWordWrap(True)
        last_text.addWidget(self.last_take_name)
        last_text.addWidget(self.last_take_meta)
        last_text.addWidget(self.last_take_note)
        last_row.addLayout(last_text, 1)
        self.last_take_play = QPushButton()
        self.last_take_play.setObjectName("MiniPlayButton")
        self.last_take_play.setIcon(_ui_icon("play"))
        self.last_take_play.setIconSize(QSize(20, 20))
        self.last_take_play.setFixedSize(40, 40)
        self.last_take_play.clicked.connect(self.play_last)
        last_row.addWidget(self.last_take_play)
        last_l.addLayout(last_row)
        ps.addWidget(last_panel, 4)

        sep1 = QFrame()
        sep1.setObjectName("StripDivider")
        sep1.setFrameShape(QFrame.VLine)
        ps.addWidget(sep1)

        history = QWidget()
        history_l = QVBoxLayout(history)
        history_l.setContentsMargins(0, 0, 0, 0)
        history_l.setSpacing(2)
        htitle = QLabel("TAKE HISTORY")
        htitle.setObjectName("StripTitle")
        history_l.addWidget(htitle)
        self.history_rows = []
        for _ in range(3):
            row_label = QLabel("—")
            row_label.setObjectName("HistoryRow")
            row_label.setMinimumHeight(20)
            history_l.addWidget(row_label)
            self.history_rows.append(row_label)
        ps.addWidget(history, 3)

        sep2 = QFrame()
        sep2.setObjectName("StripDivider")
        sep2.setFrameShape(QFrame.VLine)
        ps.addWidget(sep2)

        notes_compact = QWidget()
        nc_l = QVBoxLayout(notes_compact)
        nc_l.setContentsMargins(0, 0, 0, 0)
        nc_l.setSpacing(4)
        ntitle = QLabel("NOTES")
        ntitle.setObjectName("StripTitle")
        nc_l.addWidget(ntitle)
        self.quick_notes = QTextEdit()
        self.quick_notes.setObjectName("QuickNotes")
        self.quick_notes.setPlaceholderText("Current take note…")
        self.quick_notes.setMaximumHeight(72)
        nc_l.addWidget(self.quick_notes)
        ps.addWidget(notes_compact, 4)
        record_l.addWidget(production_strip)

        # Persistent status message (kept visually quiet).
        self.status_text = QLabel("Select an input interface and start audio.")
        self.status_text.setObjectName("FooterMessage")
        self.status_text.setWordWrap(False)
        self.workspace.addTab(record_page, "Record")

        # TAKES WORKSPACE ==================================================
        takes_page = QWidget()
        takes_page.setObjectName("WorkspacePage")
        tkl = QVBoxLayout(takes_page)
        tkl.setContentsMargins(8, 8, 8, 8)
        tkl.setSpacing(10)
        tk_head = QHBoxLayout()
        tk_head.addWidget(_icon_label("takes", 24))
        tk_title = QLabel("TAKES")
        tk_title.setObjectName("WorkspaceTitle")
        tk_head.addWidget(tk_title)
        tk_head.addStretch(1)
        tkl.addLayout(tk_head)
        tk_sub = QLabel("Completed recordings · newest first")
        tk_sub.setObjectName("AppSubtitle")
        tkl.addWidget(tk_sub)
        self.take_table = QTableWidget(0, 6)
        self.take_table.setObjectName("TakeTable")
        self.take_table.setHorizontalHeaderLabels(["★", "ROLL", "SCENE", "TAKE", "DURATION", "FILE"])
        self.take_table.verticalHeader().setVisible(False)
        self.take_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.take_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.take_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.take_table.setShowGrid(False)
        header = self.take_table.horizontalHeader()
        for col in range(5):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.take_table.itemDoubleClicked.connect(lambda _item: self.play_selected_take())
        tkl.addWidget(self.take_table, 1)
        tbtn = QHBoxLayout()
        refresh_takes = QPushButton("Refresh")
        _button_icon(refresh_takes, "refresh")
        refresh_takes.clicked.connect(self.refresh_take_browser)
        play_selected = QPushButton("Play Selected")
        _button_icon(play_selected, "play")
        play_selected.setProperty("role", "primary")
        play_selected.clicked.connect(self.play_selected_take)
        reveal = QPushButton("Reveal in Folder")
        _button_icon(reveal, "reveal")
        reveal.clicked.connect(self.show_selected_take_folder)
        tbtn.addWidget(refresh_takes)
        tbtn.addWidget(play_selected)
        tbtn.addWidget(reveal)
        tbtn.addStretch(1)
        tkl.addLayout(tbtn)
        self.workspace.addTab(takes_page, "Takes")

        # NOTES WORKSPACE ==================================================
        notes_page = QWidget()
        nl = QVBoxLayout(notes_page)
        nl.setContentsMargins(16, 16, 16, 16)
        nl.setSpacing(10)
        nh = QHBoxLayout()
        nh.addWidget(_icon_label("notes", 24))
        nt = QLabel("TAKE NOTES")
        nt.setObjectName("WorkspaceTitle")
        nh.addWidget(nt)
        nh.addStretch(1)
        nl.addLayout(nh)
        ns = QLabel("Notes are written into the completed take metadata and sound report.")
        ns.setObjectName("AppSubtitle")
        nl.addWidget(ns)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Performance, noise, wild line, wardrobe, aircraft, room tone…")
        nl.addWidget(self.notes, 1)
        self.quick_notes.textChanged.connect(self._sync_notes_from_quick)
        self.notes.textChanged.connect(self._sync_notes_from_full)
        self.workspace.addTab(notes_page, "Notes")

        # REMOTE WORKSPACE =================================================
        remote_page = QWidget()
        rpl = QVBoxLayout(remote_page)
        rpl.setContentsMargins(16, 16, 16, 16)
        rpl.setSpacing(10)
        rhead = QHBoxLayout()
        rhead.addWidget(_icon_label("remote", 24))
        rtitle = QLabel("REMOTE CONTROL")
        rtitle.setObjectName("WorkspaceTitle")
        rhead.addWidget(rtitle)
        rhead.addStretch(1)
        rpl.addLayout(rhead)
        self.remote_url_label = QLabel("Starting remote server…")
        self.remote_url_label.setObjectName("NetworkAddress")
        self.remote_url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rpl.addWidget(self.remote_url_label)
        self.remote_pin_label = QLabel(f"PAIRING CODE   {self.remote_token}")
        self.remote_pin_label.setObjectName("PairingCode")
        rpl.addWidget(self.remote_pin_label)
        rhelp = QLabel("Phones, tablets and the ESP32 remote must be on the same local network as this recorder.")
        rhelp.setObjectName("AppSubtitle")
        rhelp.setWordWrap(True)
        rpl.addWidget(rhelp)
        rb = QHBoxLayout()
        qr_button = QPushButton("Show Pairing QR")
        _button_icon(qr_button, "qr")
        qr_button.setProperty("role", "primary")
        qr_button.clicked.connect(self.show_remote_qr)
        open_remote = QPushButton("Open Web Remote")
        _button_icon(open_remote, "browser")
        open_remote.clicked.connect(self.open_web_remote)
        rb.addWidget(qr_button)
        rb.addWidget(open_remote)
        rb.addStretch(1)
        rpl.addLayout(rb)
        rpl.addStretch(1)
        self.workspace.addTab(remote_page, "Remote")

        # SYSTEM / ADVANCED AUDIO =========================================
        system_page = QWidget()
        spl = QVBoxLayout(system_page)
        spl.setContentsMargins(16, 16, 16, 16)
        spl.setSpacing(10)
        sh = QHBoxLayout()
        sh.addWidget(_icon_label("system", 24))
        st = QLabel("SYSTEM & AUDIO SETUP")
        st.setObjectName("WorkspaceTitle")
        sh.addWidget(st)
        sh.addStretch(1)
        spl.addLayout(sh)
        audio_setup_note = QLabel("Input and output routing, channel count, buffer and pre-roll.")
        audio_setup_note.setObjectName("AppSubtitle")
        spl.addWidget(audio_setup_note)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        self.system_input_combo = DeviceComboBox()
        self.system_input_combo.setObjectName("SystemInputDeviceCombo")
        self.output_combo = DeviceComboBox()
        self.sample_combo = QComboBox()
        self.sample_combo.addItems(["48000", "96000"])
        self.channels_spin = QSpinBox()
        self.channels_spin.setRange(1, self.MAX_TRACK_ROWS)
        self.channels_spin.setValue(4)
        self.buffer_combo = QComboBox()
        self.buffer_combo.addItems(["256", "512", "1024"])
        self.buffer_combo.setCurrentText("512")
        self.preroll_spin = QDoubleSpinBox()
        self.preroll_spin.setRange(0.0, 10.0)
        self.preroll_spin.setSingleStep(1.0)
        self.preroll_spin.setSuffix(" sec")
        self.preroll_spin.setValue(5.0)
        fields = (("INPUT DEVICE", self.system_input_combo), ("OUTPUT DEVICE", self.output_combo), ("SAMPLE RATE", self.sample_combo), ("INPUT CHANNELS", self.channels_spin), ("BUFFER", self.buffer_combo), ("PRE-ROLL", self.preroll_spin))
        for i, (name, w) in enumerate(fields):
            lab = QLabel(name)
            lab.setObjectName("FieldLabel")
            grid.addWidget(lab, (i // 2) * 2, i % 2)
            grid.addWidget(w, (i // 2) * 2 + 1, i % 2)
        spl.addLayout(grid)
        ab = QHBoxLayout()
        refresh_button = QPushButton("Refresh Devices")
        _button_icon(refresh_button, "refresh")
        refresh_button.clicked.connect(self._load_devices)
        self.system_apply_audio_button = QPushButton("Start / Apply Audio")
        _button_icon(self.system_apply_audio_button, "play")
        self.system_apply_audio_button.setProperty("role", "primary")
        self.system_apply_audio_button.clicked.connect(self.apply_audio)
        ab.addWidget(refresh_button)
        ab.addWidget(self.system_apply_audio_button)
        ab.addStretch(1)
        spl.addLayout(ab)
        diag_box = QFrame()
        diag_box.setObjectName("DiagnosticsPanel")
        dg = QGridLayout(diag_box)
        dg.setContentsMargins(14, 12, 14, 12)
        self.diag_audio = QLabel("Not configured")
        self.diag_xruns = QLabel("0")
        self.diag_drops = QLabel("0")
        self.diag_queue = QLabel("0%")
        self.diag_disk = QLabel("--")
        self.diag_remote = QLabel("--")
        for i, (name, val) in enumerate((("Audio", self.diag_audio), ("XRUNs", self.diag_xruns), ("Dropped blocks", self.diag_drops), ("Writer queue", self.diag_queue), ("Disk", self.diag_disk), ("Remote", self.diag_remote))):
            key = QLabel(name.upper())
            key.setObjectName("FieldLabel")
            val.setObjectName("DiagnosticValue")
            dg.addWidget(key, i, 0)
            dg.addWidget(val, i, 1)
        spl.addWidget(diag_box)
        sysb = QHBoxLayout()
        report = QPushButton("Open Sound Report")
        _button_icon(report, "report")
        report.clicked.connect(self.open_sound_report)
        save = QPushButton("Save Diagnostics")
        _button_icon(save, "diagnostics")
        save.clicked.connect(self.save_diagnostics)
        sysb.addWidget(report)
        sysb.addWidget(save)
        sysb.addStretch(1)
        spl.addLayout(sysb)
        spl.addStretch(1)
        self.workspace.addTab(system_page, "System")

        # Global footer ----------------------------------------------------
        footer = QFrame()
        footer.setObjectName("FooterBar")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(4, 3, 4, 1)
        self.footer_state = QLabel("●  Ready")
        self.footer_state.setObjectName("FooterReady")
        fl.addWidget(self.footer_state)
        fl.addWidget(self.status_text, 1)
        self.footer_project = QLabel(f"Project: {self.session.project_name}")
        self.footer_project.setObjectName("FooterText")
        fl.addWidget(self.footer_project)
        self.footer_devices = QLabel("Audio devices: --")
        self.footer_devices.setObjectName("FooterText")
        fl.addWidget(self.footer_devices)
        body_l.addWidget(footer)

        self._metadata_controls = [self.roll_edit, self.scene_edit, self.take_spin, self.fps_combo]
        self._audio_controls = [self.input_combo, self.system_input_combo, self.output_combo, self.sample_combo, self.channels_spin, self.buffer_combo, self.preroll_spin, self.apply_audio_button, self.system_apply_audio_button, self.add_input_btn]
        self.roll_edit.textChanged.connect(self._update_preview)
        self.scene_edit.textChanged.connect(self._update_preview)
        self.take_spin.valueChanged.connect(self._update_preview)
        self.fps_combo.currentTextChanged.connect(self._save_settings)
        self.channels_spin.valueChanged.connect(self._set_track_visibility)
        self.channels_spin.valueChanged.connect(self._update_channel_summary)
        self.sample_combo.currentTextChanged.connect(self._update_format_summary)
        self.buffer_combo.currentTextChanged.connect(lambda value: self.quick_buffer.setText(value))
        self.preroll_spin.valueChanged.connect(lambda value: self.quick_preroll.setText(f"{value:g} sec"))
        self.input_combo.currentIndexChanged.connect(lambda _i: self._sync_input_device(self.input_combo))
        self.system_input_combo.currentIndexChanged.connect(lambda _i: self._sync_input_device(self.system_input_combo))
        self.workspace.currentChanged.connect(lambda i: [b.setChecked(n == i) for n, b in enumerate(self.nav_buttons)])
        self._update_preview()
        self._update_channel_summary(self.channels_spin.value())

    def _sync_notes_from_quick(self) -> None:
        if not hasattr(self, "notes"):
            return
        text = self.quick_notes.toPlainText()
        if self.notes.toPlainText() == text:
            return
        self.notes.blockSignals(True)
        self.notes.setPlainText(text)
        self.notes.blockSignals(False)

    def _sync_notes_from_full(self) -> None:
        if not hasattr(self, "quick_notes"):
            return
        text = self.notes.toPlainText()
        if self.quick_notes.toPlainText() == text:
            return
        self.quick_notes.blockSignals(True)
        self.quick_notes.setPlainText(text)
        self.quick_notes.blockSignals(False)

    def _update_format_summary(self, value: str | None = None) -> None:
        try:
            sample_rate = int(value or self.sample_combo.currentText())
        except Exception:
            sample_rate = 48000
        rate_text = f"{sample_rate / 1000:g} kHz"
        self.format_label.setText(f"{rate_text} · 24-bit · POLY WAV")
        if hasattr(self, "input_summary"):
            self.input_summary.setText(f"{self.channels_spin.value()} INPUT{'S' if self.channels_spin.value() != 1 else ''} · 24-bit / {rate_text}")

    def _update_channel_summary(self, value: int | None = None) -> None:
        count = int(value if value is not None else self.channels_spin.value())
        maximum = max(1, int(getattr(self, "_selected_device_max_inputs", count)))
        try:
            rate = int(self.sample_combo.currentText())
        except Exception:
            rate = 48000
        rate_text = f"{rate / 1000:g} kHz"
        if hasattr(self, "input_summary"):
            self.input_summary.setText(f"{count} INPUT{'S' if count != 1 else ''} · 24-bit / {rate_text}")
        if hasattr(self, "quick_inputs"):
            self.quick_inputs.setText(f"{count} / {maximum}")
        self._update_add_input_control()

    def _update_add_input_control(self) -> None:
        if not hasattr(self, "add_input_btn") or not hasattr(self, "channels_spin"):
            return
        current = int(self.channels_spin.value())
        maximum = max(1, min(self.MAX_TRACK_ROWS, int(getattr(self, "_selected_device_max_inputs", current))))
        can_add = current < maximum
        self.add_input_btn.setVisible(can_add)
        self.add_input_btn.setEnabled(can_add and not self.audio.recording)
        if can_add:
            self.add_input_btn.setText(f"ADD INPUT  {current + 1} OF {maximum}")
            self.add_input_btn.setToolTip(
                f"The selected interface exposes {maximum} input channels. Add input {current + 1} to this recorder layout."
            )

    def _add_input_track(self) -> None:
        if self.audio.recording:
            return
        current = int(self.channels_spin.value())
        maximum = max(1, min(self.MAX_TRACK_ROWS, int(getattr(self, "_selected_device_max_inputs", current))))
        if current >= maximum:
            self._update_add_input_control()
            return
        audio_was_ready = self.audio.stream is not None
        self.channels_spin.setValue(current + 1)
        self._set_track_visibility(self.channels_spin.value())
        self._save_settings()
        if audio_was_ready:
            self.apply_audio()
            self.status_text.setText(f"Input {current + 1} added. Audio was reconfigured to {self.channels_spin.value()} channels.")
        else:
            self.status_text.setText(f"Input {current + 1} added. Start audio when the track layout is ready.")

    def _format_recorder_time(self, seconds: float) -> str:
        seconds = max(0.0, float(seconds))
        whole = int(seconds)
        hours, rem = divmod(whole, 3600)
        minutes, secs = divmod(rem, 60)
        try:
            fps_value = float(self.fps_combo.currentText())
        except Exception:
            fps_value = 24.0
        nominal_fps = max(1, int(round(fps_value)))
        frames = min(nominal_fps - 1, int((seconds - whole) * nominal_fps))
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

    def _set_recorder_badge(self, text: str, tone: str = "idle") -> None:
        if not hasattr(self, "recorder_state_badge"):
            return
        self.recorder_state_badge.setText(text)
        self.recorder_state_badge.setProperty("tone", tone)
        self.recorder_state_badge.style().unpolish(self.recorder_state_badge)
        self.recorder_state_badge.style().polish(self.recorder_state_badge)
        self.recorder_state_badge.update()

    def _update_compact_take_panel(self, takes: list[dict]) -> None:
        if not hasattr(self, "last_take_name"):
            return
        if not takes:
            self.last_take_name.setText("No completed take")
            self.last_take_meta.setText("—")
            self.last_take_note.setText("")
            self.last_take_icon.setPixmap(_ui_icon("waveform").pixmap(QSize(28, 28)))
            for row in self.history_rows:
                row.setText("—")
            return

        latest = takes[0]
        prefix = "★  " if latest.get("circle") else ""
        self.last_take_name.setText(prefix + str(latest.get("file", "")))
        duration = format_duration(float(latest.get("duration_seconds", 0.0)))
        recorded_at = str(latest.get("recorded_at", ""))
        time_text = recorded_at[11:19] if len(recorded_at) >= 19 else ""
        channels = int(latest.get("channels", 0) or 0)
        self.last_take_meta.setText(f"{duration}   ·   {channels}ch" + (f"   ·   {time_text}" if time_text else ""))
        note = str(latest.get("notes", "")).strip()
        self.last_take_note.setText(note or "No note")
        self.last_take_icon.setPixmap(_ui_icon("circle" if latest.get("circle") else "waveform").pixmap(QSize(28, 28)))
        for index, row in enumerate(self.history_rows):
            if index < len(takes):
                take = takes[index]
                mark = "★" if take.get("circle") else "○"
                row.setText(f"{take.get('file', '')}    {format_duration(float(take.get('duration_seconds', 0.0)))}    {mark}")
            else:
                row.setText("—")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "main_splitter"):
            target = Qt.Vertical if self.width() < 1040 else Qt.Horizontal
            if self.main_splitter.orientation() != target:
                self.main_splitter.setOrientation(target)
                self.main_splitter.setSizes([620, 280] if target == Qt.Vertical else [900, 330])

    def _install_shortcuts(self) -> None:
        bindings = [
            ("F9", self.toggle_record),
            ("Esc", self.stop_all),
            ("F8", self.play_last),
            ("Ctrl+N", self.next_take),
            ("Ctrl+Shift+C", lambda: self.circle_btn.click()),
        ]
        self._shortcuts = []
        for sequence, callback in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _restore_ui_state(self) -> None:
        self.roll_edit.setText(str(self.settings.value("slate/roll", "A001")))
        self.scene_edit.setText(str(self.settings.value("slate/scene", "1")))
        self.take_spin.setValue(int(self.settings.value("slate/take", 1)))
        self.fps_combo.setCurrentText(str(self.settings.value("slate/fps", "23.976")))
        self.sample_combo.setCurrentText(str(self.settings.value("audio/sample_rate", "48000")))
        self.channels_spin.setValue(int(self.settings.value("audio/channels", 4)))
        self.buffer_combo.setCurrentText(str(self.settings.value("audio/blocksize", "512")))
        self.preroll_spin.setValue(float(self.settings.value("audio/preroll", 5.0)))
        self.awake_check.setChecked(str(self.settings.value("system/keep_awake", "true")).lower() in ("1", "true", "yes"))
        raw_names = str(self.settings.value("tracks/names", ""))
        if raw_names:
            try:
                names = json.loads(raw_names)
                for index, name in enumerate(names[: len(self.track_rows)]):
                    self.track_rows[index].name_edit.setText(str(name))
            except Exception:
                pass
        geometry = self.settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        splitter = self.settings.value("window/splitter")
        if splitter:
            self.main_splitter.restoreState(splitter)
        self._set_track_visibility(self.channels_spin.value())

    def _save_settings(self) -> None:
        self.settings.setValue("project/path", str(self.session.project_dir))
        self.settings.setValue("slate/roll", self.roll_edit.text())
        self.settings.setValue("slate/scene", self.scene_edit.text())
        self.settings.setValue("slate/take", self.take_spin.value())
        self.settings.setValue("slate/fps", self.fps_combo.currentText())
        self.settings.setValue("audio/sample_rate", self.sample_combo.currentText())
        self.settings.setValue("audio/channels", self.channels_spin.value())
        self.settings.setValue("audio/blocksize", self.buffer_combo.currentText())
        self.settings.setValue("audio/preroll", self.preroll_spin.value())
        self.settings.setValue("system/keep_awake", self.awake_check.isChecked())
        self.settings.setValue("tracks/names", json.dumps([row.track_name() for row in self.track_rows]))
        if hasattr(self, "input_combo") and self.input_combo.currentIndex() >= 0:
            self.settings.setValue("audio/input_name", self.input_combo.currentText())
        if hasattr(self, "output_combo") and self.output_combo.currentIndex() >= 0:
            self.settings.setValue("audio/output_name", self.output_combo.currentText())
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/splitter", self.main_splitter.saveState())
        self.settings.sync()


    def _set_power_mode(self, enabled: bool) -> None:
        if enabled:
            active = self.power_inhibitor.enable()
            if active:
                self.status_text.setText("Idle sleep prevention is enabled. The display may still turn off normally.")
            else:
                self.status_text.setText("Sleep prevention is unavailable on this system; check OS power settings before a shoot.")
        else:
            self.power_inhibitor.disable()
        self._save_settings()

    def _load_devices(self) -> None:
        saved_input = str(self.settings.value("audio/input_name", ""))
        saved_output = str(self.settings.value("audio/output_name", ""))
        input_selectors = [self.input_combo, self.system_input_combo]
        for combo in input_selectors + [self.output_combo]:
            combo.blockSignals(True)
            combo.clear()
        try:
            hostapis = AudioEngine.hostapis()
            self._devices_cache = AudioEngine.devices()
            best_input = -1
            best_output = -1
            for device in self._devices_cache:
                host = hostapis[device.hostapi]["name"] if device.hostapi < len(hostapis) else "Host"
                label = f"{device.name}  [{host}]"
                if device.max_input_channels > 0:
                    for combo in input_selectors:
                        combo.addItem(label, device.index)
                    idx = self.input_combo.count() - 1
                    upper = device.name.upper()
                    if saved_input and saved_input == label:
                        best_input = idx
                    elif best_input < 0 and ("UMC404" in upper or "UMC 404" in upper):
                        best_input = idx
                if device.max_output_channels > 0:
                    self.output_combo.addItem(label, device.index)
                    idx = self.output_combo.count() - 1
                    upper = device.name.upper()
                    if saved_output and saved_output == label:
                        best_output = idx
                    elif best_output < 0 and ("UMC404" in upper or "UMC 404" in upper):
                        best_output = idx
            if best_input >= 0:
                for combo in input_selectors:
                    combo.setCurrentIndex(best_input)
            elif self.input_combo.count() > 0:
                for combo in input_selectors:
                    combo.setCurrentIndex(0)
            if best_output >= 0:
                self.output_combo.setCurrentIndex(best_output)
            elif self.output_combo.count() > 0:
                self.output_combo.setCurrentIndex(0)
            self.status_text.setText(f"Found {self.input_combo.count()} input device(s). Select one and choose Start / Apply Audio.")
            if hasattr(self, "footer_devices"):
                self.footer_devices.setText(f"{self.input_combo.count()} input device(s) found")
        except Exception as exc:
            LOGGER.exception("Audio device enumeration failed")
            QMessageBox.critical(self, "Audio Device Error", str(exc))
        finally:
            for combo in input_selectors + [self.output_combo]:
                combo.blockSignals(False)
        self._input_device_changed()

    def _sync_input_device(self, source: QComboBox) -> None:
        data = source.currentData()
        if data is None:
            return
        for combo in (self.input_combo, self.system_input_combo):
            if combo is source:
                continue
            target = combo.findData(data)
            if target >= 0 and combo.currentIndex() != target:
                combo.blockSignals(True)
                combo.setCurrentIndex(target)
                combo.blockSignals(False)
        self._input_device_changed()
        self._save_settings()

    def _input_device_changed(self) -> None:
        data = self.input_combo.currentData()
        if data is None:
            self._selected_device_max_inputs = 1
            self._update_add_input_control()
            return
        try:
            index = int(data)
            device = next((d for d in self._devices_cache if d.index == index), None)
            if device:
                self._selected_device_max_inputs = min(self.MAX_TRACK_ROWS, max(1, int(device.max_input_channels)))
                self.channels_spin.setMaximum(self._selected_device_max_inputs)
                if self.channels_spin.value() > self._selected_device_max_inputs:
                    self.channels_spin.setValue(self._selected_device_max_inputs)
                self.device_hint.setText(
                    f"{device.max_input_channels} hardware input channel(s) available on {device.name}."
                )
                rate_text = f"{int(self.sample_combo.currentText()) // 1000}k/24" if hasattr(self, "sample_combo") else "48k/24"
                self.audio_pill.set_detail(f"{device.name} · {rate_text}")
                self._update_channel_summary(self.channels_spin.value())
        except Exception:
            self._selected_device_max_inputs = max(1, self.channels_spin.value())
        self._update_add_input_control()

    def _set_track_visibility(self, channels: int) -> None:
        channels = max(1, min(int(channels), len(self.track_rows)))
        for index, row in enumerate(self.track_rows):
            row.setVisible(index < channels)
        self._update_channel_summary(channels)
        self._update_preview()

    def choose_project(self) -> None:
        if self.audio.recording:
            QMessageBox.warning(self, "Recording in Progress", "Stop the current recording before changing projects.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Choose Film Project Folder", str(self.session.project_dir))
        if not folder:
            return
        try:
            self.session = ProjectSession(Path(folder))
            self.session.ensure_writable()
            self.project_title.setText(self.session.project_name)
            self.project_subtitle.setText("ACTIVE PROJECT")
            if hasattr(self, "footer_project"):
                self.footer_project.setText(f"Project: {self.session.project_name}")
            self._save_settings()
            self._update_preview()
            self.refresh_take_browser()
            self.status_text.setText(f"Project: {self.session.project_dir}")
            self._check_recovery()
        except Exception as exc:
            QMessageBox.critical(self, "Project Folder Error", str(exc))

    def open_project_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session.project_dir)))

    def open_sound_report(self) -> None:
        try:
            report = self.session.rebuild_sound_report()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(report)))
        except Exception as exc:
            QMessageBox.critical(self, "Sound Report Error", str(exc))

    def _check_recovery(self) -> None:
        try:
            partials = self.session.find_partial_recordings()
        except Exception:
            return
        if not partials:
            return
        names = "\n".join(f"- {path.name}" for path in partials[:8])
        if len(partials) > 8:
            names += f"\n- ...and {len(partials) - 8} more"
        answer = QMessageBox.question(
            self,
            "Unfinished Recording Found",
            "FilmSet Recorder found audio left behind by an interrupted recording:\n\n"
            f"{names}\n\nRecover these files now? The original partial files will be preserved as recovered WAV files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return
        recovered = []
        failures = []
        for path in partials:
            try:
                recovered.append(self.session.recover_partial(path))
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
        message = f"Recovered {len(recovered)} recording(s)."
        if failures:
            message += "\n\nCould not recover:\n" + "\n".join(failures[:5])
        QMessageBox.information(self, "Recovery Complete", message)

    def apply_audio(self) -> None:
        if self.audio.recording:
            return
        data = self.input_combo.currentData()
        if data is None:
            QMessageBox.warning(self, "No Input Device", "Select an audio input device first.")
            return
        try:
            self.audio.stop_playback()
            self.audio.stop_monitoring()
            self.audio.configure(
                int(data),
                channels=self.channels_spin.value(),
                sample_rate=int(self.sample_combo.currentText()),
                blocksize=int(self.buffer_combo.currentText()),
                pre_roll_seconds=float(self.preroll_spin.value()),
            )
            self.audio.set_armed_channels(self._armed_states(self.audio.channels))
            self.audio.reset_counters()
            self.audio.start_monitoring()
            self._set_track_visibility(self.audio.channels)
            self.diag_audio.setText(f"{self.audio.channels}ch / {self.audio.sample_rate // 1000}k")
            self.audio_pill.setText("AUDIO READY")
            self.audio_pill.set_tone("ready")
            selected_name = self.input_combo.currentText().split("  [", 1)[0].strip()
            self.audio_pill.set_detail(f"{selected_name} · {self.audio.sample_rate // 1000}k/24")
            if hasattr(self, "quick_audio_state"):
                self.quick_audio_state.setText("READY")
            self._set_recorder_badge("READY", "ready")
            if hasattr(self, "footer_state"):
                self.footer_state.setText("●  Ready")
            self.status_text.setText("Audio is ready. Use hardware Direct Monitor for headphones.")
            self._save_settings()
        except Exception as exc:
            LOGGER.exception("Could not start audio")
            self.audio_pill.setText("AUDIO ERROR")
            self.audio_pill.set_detail("Check interface settings")
            self.audio_pill.set_tone("danger")
            self._set_recorder_badge("AUDIO ERROR", "danger")
            if hasattr(self, "quick_audio_state"):
                self.quick_audio_state.setText("ERROR")
            QMessageBox.critical(self, "Could Not Start Audio", str(exc))

    def _armed_states(self, channels: int | None = None) -> list[bool]:
        count = channels if channels is not None else self.channels_spin.value()
        return [row.is_armed() for row in self.track_rows[: int(count)]]

    def _track_names(self, channels: int | None = None) -> list[str]:
        count = channels if channels is not None else self.channels_spin.value()
        return [row.track_name() for row in self.track_rows[: int(count)]]

    def _track_arm_changed(self, channel: int, armed: bool) -> None:
        if self.audio.recording:
            return
        if self.audio.stream is not None:
            try:
                self.audio.set_armed_channels(self._armed_states(self.audio.channels))
            except Exception:
                pass

    def _update_preview(self) -> None:
        try:
            preview = self.session.allocate_take_path(
                self.roll_edit.text(), self.scene_edit.text(), self.take_spin.value()
            ).name
        except Exception:
            preview = "--"
        self.filename_preview.setText(preview)
        self.transport_slate.setText(
            f"{self.roll_edit.text().strip() or 'ROLL'}  |  {self.scene_edit.text().strip() or 'SCENE'}  |  T{self.take_spin.value():03d}"
        )

    def _lock_recording_controls(self, locked: bool) -> None:
        for widget in self._metadata_controls + self._audio_controls:
            widget.setEnabled(not locked)
        for row in self.track_rows:
            row.set_locked(locked)
        self.next_btn.setEnabled(not locked)
        self.play_btn.setEnabled(not locked)
        self._update_add_input_control()

    def toggle_record(self) -> None:
        if self.audio.recording or self.current_take_path is not None:
            self.finish_take()
            return
        self.start_take()

    def start_take(self) -> None:
        try:
            if self.audio.stream is None:
                self.apply_audio()
                if self.audio.stream is None:
                    return
            self.session.ensure_writable()
            free_bytes = self.session.disk_free_bytes()
            if free_bytes < self.MIN_RECORD_FREE_BYTES:
                raise OSError("Less than 512 MB remains on the project drive. Recording is blocked for safety.")

            armed = self._armed_states(self.audio.channels)
            if not any(armed):
                raise RuntimeError("Enable at least one track for recording (REC).")
            self.audio.set_armed_channels(armed)

            self.circle_take = False
            self._circle_targets_last = False
            self.circle_btn.setChecked(False)
            path = self.session.allocate_take_path(
                self.roll_edit.text(), self.scene_edit.text(), self.take_spin.value()
            )
            self.current_take_snapshot = {
                "roll": self.roll_edit.text().strip() or "ROLL",
                "scene": self.scene_edit.text().strip() or "SCENE",
                "take": self.take_spin.value(),
                "frame_rate": self.fps_combo.currentText(),
                "track_names": self._track_names(self.audio.channels),
                "armed_tracks": armed,
                "recorded_at": datetime.now().isoformat(timespec="seconds"),
                "xrun_start": self.audio.xrun_count,
                "drop_start": self.audio.dropped_blocks,
                "pre_roll_seconds": float(self.preroll_spin.value()),
            }
            self.current_take_path = path
            self._writer_error_seen = None
            self._emergency_stop_triggered = False
            self._emergency_stop_reason = None
            self._last_xrun_seen = self.audio.xrun_count
            self.audio.start_recording(path)
            self._lock_recording_controls(True)
            self.record_control.set_label("STOP REC")
            self.record_btn.setIcon(_ui_icon("stop"))
            self.state_pill.setText("RECORDING")
            self.state_pill.set_tone("recording")
            self._set_recorder_badge("●  RECORDING", "recording")
            if hasattr(self, "footer_state"):
                self.footer_state.setText("●  Recording")
            self.status_text.setText(f"Recording {path.name}")
            self.reset_meter_peaks()
            LOGGER.info("Take started: %s", path)
        except Exception as exc:
            LOGGER.exception("Could not start take")
            QMessageBox.critical(self, "Record Error", str(exc))

    def finish_take(self) -> None:
        if self.current_take_path is None:
            return
        snapshot = self.current_take_snapshot or {}
        intended_path = self.current_take_path
        try:
            final_path = self.audio.stop_recording()
            if final_path is None or not final_path.exists():
                raise RuntimeError("Recorder stopped without producing a finalized WAV file.")
            info = sf.info(str(final_path))
            metadata = TakeMetadata(
                file=final_path.name,
                project=self.session.project_name,
                roll=str(snapshot.get("roll", self.roll_edit.text())),
                scene=str(snapshot.get("scene", self.scene_edit.text())),
                take=int(snapshot.get("take", self.take_spin.value())),
                recorded_at=str(snapshot.get("recorded_at", datetime.now().isoformat(timespec="seconds"))),
                duration_seconds=round(float(info.frames) / float(info.samplerate or 1), 3),
                sample_rate=int(info.samplerate),
                channels=int(info.channels),
                track_names=list(snapshot.get("track_names", self._track_names(int(info.channels)))),
                armed_tracks=list(snapshot.get("armed_tracks", self._armed_states(int(info.channels)))),
                circle=bool(self.circle_take),
                notes=self.notes.toPlainText().strip(),
                frame_rate=str(snapshot.get("frame_rate", self.fps_combo.currentText())),
                xruns=max(0, self.audio.xrun_count - int(snapshot.get("xrun_start", 0))),
                dropped_blocks=max(0, self.audio.dropped_blocks - int(snapshot.get("drop_start", 0))),
                pre_roll_seconds=float(snapshot.get("pre_roll_seconds", 0.0)),
                app_version=APP_VERSION,
            )
            self.session.write_take_metadata(final_path, metadata)
            self.last_take_path = final_path
            self.refresh_take_browser(select_id=self.session.relative_take_id(final_path))
            self._circle_targets_last = True
            # Production workflow: a cleanly finalized take advances the slate.
            # Do this only after the WAV and metadata are safely written so a
            # failed/partial take never silently skips a take number.
            completed_take = int(snapshot.get("take", self.take_spin.value()))
            next_take = advance_take_number(
                self.take_spin.value(), completed_take, self.take_spin.maximum()
            )
            if next_take != self.take_spin.value():
                self.take_spin.setValue(next_take)
            # Persist the advanced slate immediately so a normal restart opens
            # on the next take even if no other settings are changed.
            self._save_settings()
            self.notes.clear()
            self.status_text.setText(
                f"Saved {final_path.name}  |  {format_duration(metadata.duration_seconds)}  |  XRUN {metadata.xruns}"
            )
            LOGGER.info("Take finalized: %s", final_path)
            if self._emergency_stop_reason:
                QMessageBox.warning(self, "Safety Stop", self._emergency_stop_reason + "\n\nThe current take was stopped and finalized automatically.")
        except Exception as exc:
            LOGGER.exception("Take finalization failed")
            partial = ProjectSession.partial_path(intended_path)
            text = str(exc)
            if partial.exists():
                text += f"\n\nA recoverable partial file remains at:\n{partial}"
            QMessageBox.critical(self, "Recording Finalization Error", text)
            self.status_text.setText("Recording stopped with an error. Check the partial file and diagnostics.")
        finally:
            self.current_take_path = None
            self.current_take_snapshot = None
            self._lock_recording_controls(False)
            self.record_control.set_label("RECORD")
            self.record_btn.setIcon(_ui_icon("record"))
            ready = self.audio.stream is not None
            self.state_pill.setText("READY" if ready else "IDLE")
            self.state_pill.set_tone("ready" if ready else "neutral")
            self._set_recorder_badge("READY" if ready else "IDLE", "ready" if ready else "idle")
            if hasattr(self, "footer_state"):
                self.footer_state.setText("●  Ready" if ready else "○  Idle")
            self._update_preview()

    def stop_all(self) -> None:
        if self.audio.recording or self.current_take_path is not None:
            self.finish_take()
        else:
            self.audio.stop_playback()
            if self.audio.stream is not None:
                self.state_pill.setText("READY")
                self.state_pill.set_tone("ready")
                self._set_recorder_badge("READY", "ready")
                self.status_text.setText("Playback stopped. Audio ready.")

    def _play_path(self, path: Path) -> None:
        if self.audio.recording:
            return
        path = Path(path)
        if not path.exists():
            self.status_text.setText("Selected take is no longer available.")
            return
        try:
            output = self.output_combo.currentData()
            self.audio.play_file(path, int(output) if output is not None else None)
            self.state_pill.setText("PLAYBACK")
            self.state_pill.set_tone("neutral")
            self._set_recorder_badge("PLAYBACK", "playback")
            self.status_text.setText(f"Playing {path.name} as a stereo dialog mix.")
        except Exception as exc:
            LOGGER.exception("Playback failed")
            QMessageBox.critical(self, "Playback Error", str(exc))

    def play_last(self) -> None:
        if not self.last_take_path or not self.last_take_path.exists():
            takes = self.session.list_takes(limit=1)
            if takes:
                try:
                    self.last_take_path = self.session.resolve_take_id(takes[0]["id"])
                except Exception:
                    self.last_take_path = None
        if not self.last_take_path:
            self.status_text.setText("No completed take is available for playback.")
            return
        self._play_path(self.last_take_path)

    def refresh_take_browser(self, select_id: str | None = None) -> None:
        if not hasattr(self, "take_table"):
            return
        try:
            takes = self.session.list_takes()
        except Exception as exc:
            LOGGER.warning("Could not refresh take playlist: %s", exc)
            return
        self._update_compact_take_panel(takes)
        self.take_table.setRowCount(len(takes))
        selected_row = -1
        for row, take in enumerate(takes):
            values = [
                "★" if take.get("circle") else "",
                str(take.get("roll", "")),
                str(take.get("scene", "")),
                str(take.get("take", "")),
                format_duration(float(take.get("duration_seconds", 0.0))),
                str(take.get("file", "")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, take.get("id", ""))
                if column == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.take_table.setItem(row, column, item)
            if select_id and take.get("id") == select_id:
                selected_row = row
        if selected_row >= 0:
            self.take_table.selectRow(selected_row)
        elif takes and self.take_table.currentRow() < 0:
            self.take_table.selectRow(0)

    def _selected_take_id(self) -> str:
        if not hasattr(self, "take_table"):
            return ""
        row = self.take_table.currentRow()
        if row < 0:
            return ""
        item = self.take_table.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item else ""

    def play_selected_take(self) -> None:
        take_id = self._selected_take_id()
        if not take_id:
            self.status_text.setText("Select a take in the Takes tab first.")
            return
        try:
            self._play_path(self.session.resolve_take_id(take_id))
        except Exception as exc:
            QMessageBox.warning(self, "Take Playback", str(exc))

    def show_selected_take_folder(self) -> None:
        take_id = self._selected_take_id()
        if not take_id:
            return
        try:
            path = self.session.resolve_take_id(take_id)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
        except Exception as exc:
            QMessageBox.warning(self, "Take Folder", str(exc))

    def next_take(self) -> None:
        if self.audio.recording:
            return
        self.audio.stop_playback()
        self.take_spin.setValue(self.take_spin.value() + 1)
        self.notes.clear()
        self.circle_take = False
        self._circle_targets_last = False
        self.circle_btn.setChecked(False)
        self._update_preview()
        self._save_settings()

    def set_circle(self, checked: bool) -> None:
        self.circle_take = bool(checked)
        if self.audio.recording:
            self.status_text.setText("Current take marked CIRCLE." if checked else "Circle mark removed from current take.")
            return
        if self._circle_targets_last and self.last_take_path and self.last_take_path.exists():
            try:
                self.session.update_take_metadata(self.last_take_path, circle=bool(checked))
                self.status_text.setText(
                    f"{self.last_take_path.name} {'marked CIRCLE' if checked else 'circle mark removed'}."
                )
                self.refresh_take_browser(select_id=self.session.relative_take_id(self.last_take_path))
            except Exception as exc:
                QMessageBox.warning(self, "Metadata Update Error", str(exc))

    def reset_meter_peaks(self) -> None:
        for row in self.track_rows:
            row.meter.reset_peak()

    def _meter_from_audio_thread(self, values: list[float], rms_values: list[float] | None = None) -> None:
        rms_values = list(rms_values or values)
        try:
            while self.meter_queue.qsize() > 2:
                self.meter_queue.get_nowait()
            self.meter_queue.put_nowait((list(values), rms_values))
        except queue.Full:
            pass

    def _tick(self) -> None:
        latest = None
        while True:
            try:
                latest = self.meter_queue.get_nowait()
            except queue.Empty:
                break
        if latest is not None:
            peaks, rms_values = latest
            self.last_meter_values = list(peaks)
            self.last_rms_values = list(rms_values)
            for index, db in enumerate(peaks[: len(self.track_rows)]):
                rms_db = rms_values[index] if index < len(rms_values) else db
                self.track_rows[index].set_level(float(db), float(rms_db))

        if self.audio.recording:
            self.clock.setText(self._format_recorder_time(self.audio.elapsed_seconds))
        else:
            self.clock.setText("00:00:00:00")
            if self.audio.playing:
                self.state_pill.setText("PLAYBACK")
                self.state_pill.set_tone("neutral")
                self._set_recorder_badge("PLAYBACK", "playback")
            elif self.audio.stream is not None and self.current_take_path is None:
                self.state_pill.setText("READY")
                self.state_pill.set_tone("ready")
                self._set_recorder_badge("READY", "ready")

        self.diag_xruns.setText(str(self.audio.xrun_count))
        self.diag_drops.setText(str(self.audio.dropped_blocks))
        self.diag_queue.setText(f"{self.audio.writer_queue_percent:.1f}%")
        if self.audio.recording and self.audio.xrun_count > self._last_xrun_seen:
            self._last_xrun_seen = self.audio.xrun_count
            self.status_text.setText("WARNING: Audio XRUN detected during this take. Mark the take and investigate before continuing production.")
        if self.audio.recording and self.audio.writer_queue_percent >= 90.0 and not self._emergency_stop_triggered:
            self._emergency_stop_triggered = True
            self._emergency_stop_reason = "The disk-writer queue exceeded 90%, indicating the recording drive could not keep up safely."
            self.status_text.setText("SAFETY STOP: writer backlog critical. Finalizing the current take...")
            QTimer.singleShot(0, self.finish_take)

        now_ms = int(datetime.now().timestamp() * 1000)
        if now_ms - self._last_disk_update >= 1000:
            self._last_disk_update = now_ms
            self._update_disk_status()

        writer_error = self.audio.writer_error
        if writer_error and writer_error != self._writer_error_seen:
            self._writer_error_seen = writer_error
            self.state_pill.setText("REC ERROR")
            self.state_pill.set_tone("danger")
            self._set_recorder_badge("REC ERROR", "danger")
            self.status_text.setText(f"Recorder writer error: {writer_error}")

        for _ in range(12):
            try:
                payload = self.remote_commands.get_nowait()
            except queue.Empty:
                break
            self._handle_remote(payload)

        self._refresh_remote_state_cache()

    def _update_disk_status(self) -> None:
        try:
            free = self.session.disk_free_bytes()
            gb = free / (1024 ** 3)
            channels = self.audio.channels if self.audio.stream is not None else self.channels_spin.value()
            sample_rate = self.audio.sample_rate if self.audio.stream is not None else int(self.sample_combo.currentText())
            seconds = self.session.estimated_record_seconds(sample_rate, channels)
            self.diag_disk.setText(f"{gb:.1f} GB / {format_duration(seconds)}")
            self.disk_pill.setText("DISK")
            self.disk_pill.set_detail(f"{gb:.1f} GB")
            if free < self.MIN_RECORD_FREE_BYTES:
                self.disk_pill.set_tone("danger")
            elif free < 2 * 1024 ** 3:
                self.disk_pill.set_tone("warning")
            else:
                self.disk_pill.set_tone("neutral")
            if self.audio.recording and free < self.EMERGENCY_STOP_FREE_BYTES and not self._emergency_stop_triggered:
                self._emergency_stop_triggered = True
                self._emergency_stop_reason = "Project drive free space fell below 256 MB."
                self.status_text.setText("SAFETY STOP: disk space critically low. Finalizing the current take...")
                QTimer.singleShot(0, self.finish_take)
        except Exception:
            self.diag_disk.setText("Unavailable")
            self.disk_pill.setText("DISK")
            self.disk_pill.set_detail("Unavailable")
            self.disk_pill.set_tone("warning")

    def _start_remote_server(self) -> None:
        self.controller_server = ControllerServer(
            command_sink=self._enqueue_remote_command,
            state_provider=self.remote_state,
            token=self.remote_token,
            web_root=resource_path("web"),
            take_provider=lambda: self.session.list_takes(),
            take_resolver=lambda take_id: self.session.resolve_take_id(take_id),
        )
        try:
            self.controller_server.start(port=8765)
            ip = _local_ip()
            address = f"{ip}:8765"
            self.remote_address = f"http://{address}"
            self.remote_pill.setText("REMOTE")
            self.remote_pill.set_detail(address)
            self.remote_pill.set_tone("ready")
            self.diag_remote.setText(f"{address} / PIN {self.remote_token}")
            if hasattr(self, "remote_url_label"):
                self.remote_url_label.setText(self.remote_address)
            if hasattr(self, "remote_pin_label"):
                self.remote_pin_label.setText(f"PAIRING CODE   {self.remote_token}")
        except OSError as exc:
            self.remote_pill.setText("REMOTE OFF")
            self.remote_pill.set_detail("Unavailable")
            self.remote_pill.set_tone("warning")
            self.diag_remote.setText(str(exc))
            self.remote_address = ""
            if hasattr(self, "remote_url_label"):
                self.remote_url_label.setText("Remote server unavailable")

    def show_remote_qr(self) -> None:
        if not self.remote_address:
            QMessageBox.warning(self, "Remote unavailable", "The local remote server is not currently running.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("FilmSet Recorder Remote")
        dialog.setMinimumWidth(410)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("SCAN TO OPEN REMOTE")
        heading.setObjectName("FieldLabel")
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)

        qr = qrcode.QRCode(version=None, box_size=8, border=2)
        qr.add_data(f"{self.remote_address}/#pin={self.remote_token}")
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        qimage = QImage.fromData(buffer.getvalue(), "PNG")
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setPixmap(QPixmap.fromImage(qimage).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(qr_label)

        url_label = QLabel(self.remote_address)
        url_label.setAlignment(Qt.AlignCenter)
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        url_label.setObjectName("TakePreview")
        layout.addWidget(url_label)

        pin_title = QLabel("PAIRING CODE")
        pin_title.setObjectName("FieldLabel")
        pin_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(pin_title)
        pin_label = QLabel(self.remote_token)
        pin_label.setAlignment(Qt.AlignCenter)
        pin_label.setStyleSheet("font-size: 34px; font-weight: 800; letter-spacing: 8px;")
        layout.addWidget(pin_label)

        help_label = QLabel("Connect the phone to the same Wi-Fi network and scan the code for instant pairing. Anyone who scans this QR code can control the recorder while it is visible.")
        help_label.setObjectName("Muted")
        help_label.setWordWrap(True)
        help_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(help_label)

        close_button = QPushButton("Done")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def open_web_remote(self) -> None:
        if not self.remote_address:
            QMessageBox.warning(self, "Remote unavailable", "The local remote server is not currently running.")
            return
        QDesktopServices.openUrl(QUrl(self.remote_address))

    def _enqueue_remote_command(self, payload: dict) -> None:
        try:
            self.remote_commands.put_nowait(payload)
        except queue.Full:
            LOGGER.warning("Remote command queue full")

    def _handle_remote(self, payload: dict) -> None:
        cmd = str(payload.get("command", "")).strip().lower()
        if cmd == "record" and not self.audio.recording and self.current_take_path is None:
            self.start_take()
        elif cmd == "stop":
            self.stop_all()
        elif cmd == "play":
            self.play_last()
        elif cmd == "play_take" and not self.audio.recording:
            try:
                self._play_path(self.session.resolve_take_id(str(payload.get("take_id", ""))))
            except Exception as exc:
                self.status_text.setText(f"Remote playback failed: {exc}")
        elif cmd == "next_take":
            self.next_take()
        elif cmd in ("circle", "toggle_circle"):
            self.circle_btn.setChecked(not self.circle_btn.isChecked())
            self.set_circle(self.circle_btn.isChecked())
        elif cmd == "set_scene" and "scene" in payload and not self.audio.recording:
            self.scene_edit.setText(str(payload["scene"]))
        elif cmd == "set_take" and "take" in payload and not self.audio.recording:
            try:
                self.take_spin.setValue(int(payload["take"]))
            except (TypeError, ValueError):
                pass

    def _refresh_remote_state_cache(self) -> None:
        try:
            free = self.session.disk_free_bytes()
            gb = free / (1024 ** 3)
            channels = self.audio.channels if self.audio.stream is not None else self.channels_spin.value()
            sample_rate = self.audio.sample_rate if self.audio.stream is not None else int(self.sample_combo.currentText())
            remaining = self.session.estimated_record_seconds(sample_rate, channels)
            disk_display = f"{gb:.1f} GB / {format_duration(remaining)}"
        except Exception:
            disk_display = "Unavailable"
        state = {
            "version": APP_VERSION,
            "recording": self.audio.recording,
            "playing": self.audio.playing,
            "elapsed": round(self.audio.elapsed_seconds, 3) if self.audio.recording else 0.0,
            "roll": self.roll_edit.text(),
            "scene": self.scene_edit.text(),
            "take": self.take_spin.value(),
            "circle": self.circle_take,
            "last_file": self.last_take_path.name if self.last_take_path else "",
            "last_file_id": self.session.relative_take_id(self.last_take_path) if self.last_take_path and self.last_take_path.exists() else "",
            "xruns": self.audio.xrun_count,
            "dropped_blocks": self.audio.dropped_blocks,
            "writer_queue_percent": round(self.audio.writer_queue_percent, 1),
            "meters": [round(v, 1) for v in self.last_meter_values[: self.channels_spin.value()]],
            "tracks": self._track_names(self.channels_spin.value()),
            "armed": self._armed_states(self.channels_spin.value()),
            "project": self.session.project_name,
            "audio_ready": self.audio.stream is not None,
            "disk_display": disk_display,
            "remote_url": self.remote_address,
        }
        with self._remote_state_lock:
            self._remote_state_cache = state

    def remote_state(self) -> dict:
        with self._remote_state_lock:
            return dict(self._remote_state_cache)

    def save_diagnostics(self) -> None:
        default = self.session.project_dir / f"FilmSetRecorder_Diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filename, _ = QFileDialog.getSaveFileName(self, "Save FilmSet Recorder Diagnostics", str(default), "Text Files (*.txt)")
        if not filename:
            return
        try:
            hostapis = AudioEngine.hostapis()
            devices = AudioEngine.devices()
            lines = [
                f"{APP_NAME} {APP_VERSION}",
                f"Generated: {datetime.now().isoformat(timespec='seconds')}",
                f"OS: {platform.platform()}",
                f"Python: {platform.python_version()}",
                f"Project: {self.session.project_dir}",
                f"Input selection: {self.input_combo.currentText()}",
                f"Output selection: {self.output_combo.currentText()}",
                f"Sample rate: {self.sample_combo.currentText()}",
                f"Channels: {self.channels_spin.value()}",
                f"Buffer: {self.buffer_combo.currentText()}",
                f"Pre-roll: {self.preroll_spin.value()}",
                f"XRUNs: {self.audio.xrun_count}",
                f"Dropped blocks: {self.audio.dropped_blocks}",
                f"Writer queue: {self.audio.writer_queue_percent:.1f}%",
                "",
                "HOST APIS",
            ]
            for index, api in enumerate(hostapis):
                lines.append(f"[{index}] {api.get('name', 'Unknown')}")
            lines.extend(["", "AUDIO DEVICES"])
            for device in devices:
                host = hostapis[device.hostapi]["name"] if device.hostapi < len(hostapis) else "Unknown"
                lines.append(
                    f"[{device.index}] {device.name} | {host} | in={device.max_input_channels} | out={device.max_output_channels} | default_sr={device.default_samplerate}"
                )
            Path(filename).write_text("\n".join(lines), encoding="utf-8")
            self.status_text.setText(f"Diagnostics saved to {filename}")
        except Exception as exc:
            QMessageBox.critical(self, "Diagnostics Error", str(exc))

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<b>{APP_NAME} {APP_VERSION}</b><br><br>"
            "A production-dialogue multitrack recorder designed for film sets.<br><br>"
            "This engineering build includes crash-safe partial recordings, pre-roll, polyphonic 24-bit WAV capture, sound reports, persistent settings, and ESP32 remote control.<br><br>"
            "Before using it for irreplaceable production audio, complete extended hardware and stress testing with your exact interface and computer.",
        )

    def closeEvent(self, event) -> None:
        if self.audio.recording or self.current_take_path is not None:
            answer = QMessageBox.question(
                self,
                "Recording in Progress",
                "Stop and finalize the current take before exiting?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.finish_take()
        self._save_settings()
        try:
            self.audio.stop_playback()
            self.audio.stop_monitoring()
            self.power_inhibitor.disable()
            self.controller_server.stop()
        finally:
            event.accept()


def run() -> None:
    logger = configure_logging()
    install_exception_hook(logger)
    logger.info("Starting %s %s", APP_NAME, APP_VERSION)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    product_icon = brand_icon(256)
    app.setWindowIcon(product_icon)

    win = MainWindow()
    win.setWindowIcon(product_icon)
    win.show()
    sys.exit(app.exec())
