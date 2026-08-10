from __future__ import annotations

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

import soundfile as sf
from PySide6.QtCore import QSettings, QStandardPaths, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
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
from .utils import format_duration, resource_path
from .version import APP_NAME, APP_VERSION, ORGANIZATION_NAME
from .widgets import Card, StatusPill, TrackRow, TransportButton

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


class MainWindow(QMainWindow):
    MAX_TRACK_ROWS = 16
    MIN_RECORD_FREE_BYTES = 512 * 1024 * 1024
    EMERGENCY_STOP_FREE_BYTES = 256 * 1024 * 1024

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1080, 700)
        self.resize(1420, 900)

        self.settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        self.meter_queue: queue.Queue[list[float]] = queue.Queue(maxsize=8)
        self.remote_commands: queue.Queue[dict] = queue.Queue(maxsize=64)
        self._remote_state_lock = threading.Lock()
        self._remote_state_cache: dict = {}
        self.last_meter_values: list[float] = [-80.0] * 4

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
        self._emergency_stop_triggered = False
        self._emergency_stop_reason: str | None = None
        self._last_xrun_seen = 0

        token = str(self.settings.value("remote/token", "")).strip()
        if len(token) < 4:
            token = f"{secrets.randbelow(1_000_000):06d}"
            self.settings.setValue("remote/token", token)
        self.remote_token = token

        self._build_menu()
        self._build_ui()
        self._restore_ui_state()
        self._load_devices()
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
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 18)
        outer.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.app_title = QLabel(APP_NAME.upper())
        self.app_title.setObjectName("AppTitle")
        self.project_subtitle = QLabel(self.session.project_name)
        self.project_subtitle.setObjectName("AppSubtitle")
        title_col.addWidget(self.app_title)
        title_col.addWidget(self.project_subtitle)
        header.addLayout(title_col)
        header.addStretch(1)

        self.audio_pill = StatusPill("AUDIO OFF", "neutral")
        self.remote_pill = StatusPill("REMOTE STARTING", "neutral")
        self.disk_pill = StatusPill("DISK --", "neutral")
        self.state_pill = StatusPill("IDLE", "neutral")
        for pill in (self.audio_pill, self.remote_pill, self.disk_pill, self.state_pill):
            header.addWidget(pill)
        outer.addLayout(header)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        outer.addWidget(self.main_splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        self.main_splitter.addWidget(left)

        right = QWidget()
        right.setMinimumWidth(370)
        right.setMaximumWidth(500)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)
        self.main_splitter.addWidget(right)
        self.main_splitter.setStretchFactor(0, 4)
        self.main_splitter.setStretchFactor(1, 1)

        metadata_card = Card("SLATE", "Production metadata")
        metadata_grid = QGridLayout()
        metadata_grid.setHorizontalSpacing(12)
        metadata_grid.setVerticalSpacing(7)

        self.roll_edit = QLineEdit("A001")
        self.scene_edit = QLineEdit("1")
        self.take_spin = QSpinBox()
        self.take_spin.setRange(1, 99999)
        self.take_spin.setValue(1)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["23.976", "24", "25", "29.97", "30"])

        fields = [
            ("ROLL", self.roll_edit, 0),
            ("SCENE", self.scene_edit, 1),
            ("TAKE", self.take_spin, 2),
            ("FRAME RATE", self.fps_combo, 3),
        ]
        for label_text, widget, column in fields:
            label = QLabel(label_text)
            label.setObjectName("FieldLabel")
            metadata_grid.addWidget(label, 0, column)
            metadata_grid.addWidget(widget, 1, column)
        metadata_grid.setColumnStretch(0, 1)
        metadata_grid.setColumnStretch(1, 2)
        metadata_grid.setColumnStretch(2, 1)
        metadata_grid.setColumnStretch(3, 1)
        metadata_card.body.addLayout(metadata_grid)

        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("NEXT FILE"))
        self.filename_preview = QLabel("")
        self.filename_preview.setObjectName("TakePreview")
        preview_row.addWidget(self.filename_preview, 1)
        project_button = QPushButton("Project Folder")
        project_button.clicked.connect(self.choose_project)
        preview_row.addWidget(project_button)
        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_project_folder)
        preview_row.addWidget(open_button)
        metadata_card.body.addLayout(preview_row)
        left_layout.addWidget(metadata_card)

        meters_card = Card("ISO TRACKS", "24-bit poly WAV")
        self.track_scroll = QScrollArea()
        self.track_scroll.setWidgetResizable(True)
        self.track_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        track_container = QWidget()
        self.track_layout = QVBoxLayout(track_container)
        self.track_layout.setContentsMargins(0, 0, 0, 0)
        self.track_layout.setSpacing(8)
        self.track_rows: list[TrackRow] = []
        default_names = ["Boom", "Lav A", "Lav B", "Plant"]
        for index in range(self.MAX_TRACK_ROWS):
            name = default_names[index] if index < len(default_names) else f"Input {index + 1}"
            row = TrackRow(index, name)
            row.armedChanged.connect(self._track_arm_changed)
            self.track_rows.append(row)
            self.track_layout.addWidget(row)
            row.setVisible(index < 4)
        self.track_layout.addStretch(1)
        self.track_scroll.setWidget(track_container)
        meters_card.body.addWidget(self.track_scroll, 1)
        left_layout.addWidget(meters_card, 1)

        audio_card = Card("AUDIO I/O", "PortAudio device routing")
        audio_grid = QGridLayout()
        audio_grid.setHorizontalSpacing(10)
        audio_grid.setVerticalSpacing(8)
        self.input_combo = QComboBox()
        self.output_combo = QComboBox()
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

        audio_fields = [
            ("INPUT DEVICE", self.input_combo),
            ("OUTPUT DEVICE", self.output_combo),
            ("SAMPLE RATE", self.sample_combo),
            ("INPUT CHANNELS", self.channels_spin),
            ("BUFFER", self.buffer_combo),
            ("PRE-ROLL", self.preroll_spin),
        ]
        for row_idx, (label_text, widget) in enumerate(audio_fields):
            label = QLabel(label_text)
            label.setObjectName("FieldLabel")
            audio_grid.addWidget(label, row_idx * 2, 0)
            audio_grid.addWidget(widget, row_idx * 2 + 1, 0)
        audio_card.body.addLayout(audio_grid)

        audio_buttons = QHBoxLayout()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._load_devices)
        self.apply_audio_button = QPushButton("Apply / Start Audio")
        self.apply_audio_button.setProperty("role", "accent")
        self.apply_audio_button.clicked.connect(self.apply_audio)
        audio_buttons.addWidget(refresh_button)
        audio_buttons.addWidget(self.apply_audio_button, 1)
        audio_card.body.addLayout(audio_buttons)

        self.awake_check = QCheckBox("Keep computer awake while recorder is open")
        self.awake_check.setToolTip("Prevents normal idle sleep. It does not guarantee lid-closed operation on every computer or operating system.")
        self.awake_check.toggled.connect(self._set_power_mode)
        audio_card.body.addWidget(self.awake_check)

        monitor_note = QLabel("Use the interface hardware Direct Monitor path for zero-latency headphones. Software monitoring is intentionally disabled in this build.")
        monitor_note.setObjectName("Muted")
        monitor_note.setWordWrap(True)
        audio_card.body.addWidget(monitor_note)
        right_layout.addWidget(audio_card)

        notes_card = Card("TAKE NOTES", "Saved with every take")
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Performance notes, noise, wild line, airplane, wardrobe rustle...")
        self.notes.setMinimumHeight(130)
        notes_card.body.addWidget(self.notes)
        right_layout.addWidget(notes_card)

        diagnostic_card = Card("SYSTEM", "Recorder health")
        diag_grid = QGridLayout()
        diag_grid.setHorizontalSpacing(10)
        diag_grid.setVerticalSpacing(7)
        self.diag_audio = QLabel("Not configured")
        self.diag_xruns = QLabel("0")
        self.diag_drops = QLabel("0")
        self.diag_queue = QLabel("0%")
        self.diag_disk = QLabel("--")
        self.diag_remote = QLabel("--")
        diag_items = [
            ("Audio", self.diag_audio),
            ("XRUNs", self.diag_xruns),
            ("Dropped blocks", self.diag_drops),
            ("Writer queue", self.diag_queue),
            ("Disk", self.diag_disk),
            ("Remote", self.diag_remote),
        ]
        for i, (name, value) in enumerate(diag_items):
            key = QLabel(name.upper())
            key.setObjectName("FieldLabel")
            diag_grid.addWidget(key, i, 0)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            diag_grid.addWidget(value, i, 1)
        diagnostic_card.body.addLayout(diag_grid)

        diag_buttons = QHBoxLayout()
        report_button = QPushButton("Sound Report")
        report_button.clicked.connect(self.open_sound_report)
        save_diag_button = QPushButton("Save Diagnostics")
        save_diag_button.clicked.connect(self.save_diagnostics)
        diag_buttons.addWidget(report_button)
        diag_buttons.addWidget(save_diag_button)
        diagnostic_card.body.addLayout(diag_buttons)
        right_layout.addWidget(diagnostic_card)
        right_layout.addStretch(1)

        transport_card = Card()
        transport_layout = QHBoxLayout()
        transport_layout.setSpacing(10)
        transport_card.body.addLayout(transport_layout)

        self.clock = QLabel("00:00:00.000")
        self.clock.setObjectName("RecordClock")
        self.clock.setMinimumWidth(255)
        transport_layout.addWidget(self.clock)

        clock_meta = QVBoxLayout()
        self.transport_slate = QLabel("A001 | 1 | T001")
        self.transport_slate.setObjectName("TakePreview")
        self.status_text = QLabel("Choose an input device and start audio.")
        self.status_text.setObjectName("StatusText")
        self.status_text.setWordWrap(True)
        clock_meta.addWidget(self.transport_slate)
        clock_meta.addWidget(self.status_text)
        transport_layout.addLayout(clock_meta, 1)

        self.record_btn = TransportButton("REC", "record")
        self.record_btn.clicked.connect(self.toggle_record)
        self.stop_btn = TransportButton("STOP", "stop")
        self.stop_btn.clicked.connect(self.stop_all)
        self.play_btn = TransportButton("PLAY LAST", "secondary")
        self.play_btn.clicked.connect(self.play_last)
        self.next_btn = TransportButton("NEXT TAKE", "accent")
        self.next_btn.clicked.connect(self.next_take)
        self.circle_btn = TransportButton("CIRCLE", "circle")
        self.circle_btn.setCheckable(True)
        self.circle_btn.clicked.connect(self.set_circle)

        for button in (self.record_btn, self.stop_btn, self.play_btn, self.next_btn, self.circle_btn):
            button.setMinimumWidth(115)
            transport_layout.addWidget(button)
        outer.addWidget(transport_card)

        self._metadata_controls = [self.roll_edit, self.scene_edit, self.take_spin, self.fps_combo]
        self._audio_controls = [
            self.input_combo,
            self.output_combo,
            self.sample_combo,
            self.channels_spin,
            self.buffer_combo,
            self.preroll_spin,
            self.apply_audio_button,
        ]

        self.roll_edit.textChanged.connect(self._update_preview)
        self.scene_edit.textChanged.connect(self._update_preview)
        self.take_spin.valueChanged.connect(self._update_preview)
        self.fps_combo.currentTextChanged.connect(self._save_settings)
        self.channels_spin.valueChanged.connect(self._set_track_visibility)
        self.input_combo.currentIndexChanged.connect(self._input_device_changed)
        self._update_preview()

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
        self.input_combo.blockSignals(True)
        self.output_combo.blockSignals(True)
        self.input_combo.clear()
        self.output_combo.clear()
        try:
            hostapis = AudioEngine.hostapis()
            self._devices_cache = AudioEngine.devices()
            best_input = -1
            best_output = -1
            for device in self._devices_cache:
                host = hostapis[device.hostapi]["name"] if device.hostapi < len(hostapis) else "Host"
                label = f"{device.name}  [{host}]"
                if device.max_input_channels > 0:
                    self.input_combo.addItem(label, device.index)
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
                self.input_combo.setCurrentIndex(best_input)
            if best_output >= 0:
                self.output_combo.setCurrentIndex(best_output)
            self.status_text.setText(f"Found {self.input_combo.count()} input device(s).")
        except Exception as exc:
            LOGGER.exception("Audio device enumeration failed")
            QMessageBox.critical(self, "Audio Device Error", str(exc))
        finally:
            self.input_combo.blockSignals(False)
            self.output_combo.blockSignals(False)
        self._input_device_changed()

    def _input_device_changed(self) -> None:
        data = self.input_combo.currentData()
        if data is None:
            return
        try:
            index = int(data)
            device = next((d for d in self._devices_cache if d.index == index), None)
            if device:
                self.channels_spin.setMaximum(min(self.MAX_TRACK_ROWS, max(1, device.max_input_channels)))
                if self.channels_spin.value() > device.max_input_channels:
                    self.channels_spin.setValue(device.max_input_channels)
        except Exception:
            pass

    def _set_track_visibility(self, channels: int) -> None:
        channels = max(1, min(int(channels), len(self.track_rows)))
        for index, row in enumerate(self.track_rows):
            row.setVisible(index < channels)
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
            self.project_subtitle.setText(self.session.project_name)
            self._save_settings()
            self._update_preview()
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
            self.status_text.setText("Audio is ready. Use hardware Direct Monitor for headphones.")
            self._save_settings()
        except Exception as exc:
            LOGGER.exception("Could not start audio")
            self.audio_pill.setText("AUDIO ERROR")
            self.audio_pill.set_tone("danger")
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
                raise RuntimeError("Arm at least one track before recording.")
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
            self.record_btn.setText("STOP REC")
            self.state_pill.setText("RECORDING")
            self.state_pill.set_tone("recording")
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
            self._circle_targets_last = True
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
            self.record_btn.setText("REC")
            self.state_pill.setText("READY" if self.audio.stream is not None else "IDLE")
            self.state_pill.set_tone("ready" if self.audio.stream is not None else "neutral")
            self._update_preview()

    def stop_all(self) -> None:
        if self.audio.recording or self.current_take_path is not None:
            self.finish_take()
        else:
            self.audio.stop_playback()
            if self.audio.stream is not None:
                self.state_pill.setText("READY")
                self.state_pill.set_tone("ready")
                self.status_text.setText("Playback stopped. Audio ready.")

    def play_last(self) -> None:
        if self.audio.recording:
            return
        if not self.last_take_path or not self.last_take_path.exists():
            self.status_text.setText("No completed take is available for playback.")
            return
        try:
            output = self.output_combo.currentData()
            self.audio.play_file(self.last_take_path, int(output) if output is not None else None)
            self.state_pill.setText("PLAYBACK")
            self.state_pill.set_tone("neutral")
            self.status_text.setText(f"Playing {self.last_take_path.name} as a stereo dialog mix.")
        except Exception as exc:
            LOGGER.exception("Playback failed")
            QMessageBox.critical(self, "Playback Error", str(exc))

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
            except Exception as exc:
                QMessageBox.warning(self, "Metadata Update Error", str(exc))

    def reset_meter_peaks(self) -> None:
        for row in self.track_rows:
            row.meter.reset_peak()

    def _meter_from_audio_thread(self, values: list[float]) -> None:
        try:
            while self.meter_queue.qsize() > 2:
                self.meter_queue.get_nowait()
            self.meter_queue.put_nowait(values)
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
            self.last_meter_values = list(latest)
            for index, db in enumerate(latest[: len(self.track_rows)]):
                self.track_rows[index].set_level(float(db))

        if self.audio.recording:
            self.clock.setText(format_duration(self.audio.elapsed_seconds, milliseconds=True))
        else:
            self.clock.setText("00:00:00.000")
            if self.audio.playing:
                self.state_pill.setText("PLAYBACK")
                self.state_pill.set_tone("neutral")
            elif self.audio.stream is not None and self.current_take_path is None:
                self.state_pill.setText("READY")
                self.state_pill.set_tone("ready")

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
            self.disk_pill.setText(f"DISK {gb:.1f} GB")
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
            self.disk_pill.setText("DISK ?")
            self.disk_pill.set_tone("warning")

    def _start_remote_server(self) -> None:
        self.controller_server = ControllerServer(
            command_sink=self._enqueue_remote_command,
            state_provider=self.remote_state,
            token=self.remote_token,
        )
        try:
            self.controller_server.start(port=8765)
            address = f"{_local_ip()}:8765"
            self.remote_pill.setText(f"REMOTE {address}")
            self.remote_pill.set_tone("ready")
            self.diag_remote.setText(f"{address} / PIN {self.remote_token}")
        except OSError as exc:
            self.remote_pill.setText("REMOTE OFF")
            self.remote_pill.set_tone("warning")
            self.diag_remote.setText(str(exc))

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
            "xruns": self.audio.xrun_count,
            "dropped_blocks": self.audio.dropped_blocks,
            "writer_queue_percent": round(self.audio.writer_queue_percent, 1),
            "meters": [round(v, 1) for v in self.last_meter_values[: self.channels_spin.value()]],
            "tracks": self._track_names(self.channels_spin.value()),
            "armed": self._armed_states(self.channels_spin.value()),
            "project": self.session.project_name,
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
    icon_path = resource_path("assets/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    win = MainWindow()
    if icon_path.exists():
        win.setWindowIcon(QIcon(str(icon_path)))
    win.show()
    sys.exit(app.exec())
