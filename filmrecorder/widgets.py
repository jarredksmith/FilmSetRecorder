from __future__ import annotations

import math
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .ui_icons import make_icon


class DeviceComboBox(QComboBox):
    """Dark device selector with a guaranteed visible disclosure chevron."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to choose an audio device")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor("#A9C0D5"), 1.8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        x = self.width() - 17
        y = self.height() / 2.0 - 2
        painter.drawLine(QPointF(x - 4, y), QPointF(x, y + 4))
        painter.drawLine(QPointF(x, y + 4), QPointF(x + 4, y))
        painter.end()


class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 18)
        self._layout.setSpacing(12)
        if title:
            header = QHBoxLayout()
            title_label = QLabel(title)
            title_label.setObjectName("CardTitle")
            header.addWidget(title_label)
            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setObjectName("CardSubtitle")
                subtitle_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                header.addWidget(subtitle_label, 1)
            self._layout.addLayout(header)

    @property
    def body(self) -> QVBoxLayout:
        return self._layout


class StatusPill(QFrame):
    """Compact two-line status card matching the recorder header mockup."""

    def __init__(
        self,
        text: str = "",
        tone: str = "neutral",
        icon: QIcon | None = None,
        detail: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self.setMinimumHeight(52)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 6, 12, 6)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("StatusPillIcon")
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        text_stack = QVBoxLayout()
        text_stack.setSpacing(0)
        self.text_label = QLabel(text)
        self.text_label.setObjectName("StatusPillText")
        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName("StatusPillDetail")
        self.detail_label.setVisible(bool(detail))
        text_stack.addWidget(self.text_label)
        text_stack.addWidget(self.detail_label)
        layout.addLayout(text_stack)

        if icon is not None and not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(QSize(19, 19)))
        self.set_tone(tone)

    def setText(self, text: str) -> None:
        self.text_label.setText(text)

    def text(self) -> str:
        return self.text_label.text()

    def set_detail(self, detail: str) -> None:
        detail = str(detail or "")
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)
        for child in (self.icon_label, self.text_label, self.detail_label):
            child.style().unpolish(child)
            child.style().polish(child)
        self.update()


class PeakMeter(QWidget):
    """Production-style segmented peak/RMS meter with calibrated dBFS scale."""

    SCALE = (-60, -48, -36, -24, -18, -12, -6, -3, 0)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level_db = -80.0
        self._rms_db = -80.0
        self._peak_db = -80.0
        self._peak_time = 0.0
        self._clipped_until = 0.0
        self.setMinimumHeight(58)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @property
    def level_db(self) -> float:
        return self._level_db

    @property
    def rms_db(self) -> float:
        return self._rms_db

    def set_level(self, db: float, rms_db: float | None = None) -> None:
        db = max(-80.0, min(3.0, float(db)))
        rms_db = db if rms_db is None else max(-80.0, min(3.0, float(rms_db)))
        self._level_db = db
        self._rms_db = rms_db
        now = time.monotonic()
        if db >= self._peak_db or now - self._peak_time > 1.5:
            self._peak_db = db
            self._peak_time = now
        if db >= -0.1:
            self._clipped_until = now + 2.5
        if now - self._peak_time > 1.5:
            self._peak_db = max(db, self._peak_db - 1.0)
        self.update()

    def reset_peak(self) -> None:
        self._peak_db = -80.0
        self._rms_db = -80.0
        self._peak_time = 0.0
        self._clipped_until = 0.0
        self.update()

    @staticmethod
    def _fraction(db: float) -> float:
        db = max(-60.0, min(0.0, db))
        return (db + 60.0) / 60.0

    @staticmethod
    def _segment_color(db: float, bright: bool = True) -> QColor:
        if not bright:
            return QColor("#0F2A40")
        if db < -24:
            return QColor("#04D6CC")
        if db < -12:
            return QColor("#31E95D")
        if db < -6:
            return QColor("#CDE91C")
        if db < -3:
            return QColor("#FFC326")
        return QColor("#FF454F")

    def _draw_bar(self, painter: QPainter, rect: QRectF, level_db: float, alpha: float = 1.0) -> None:
        segments = 76
        gap = 1.8
        usable = max(1.0, rect.width() - gap * (segments - 1))
        seg_w = max(1.0, usable / segments)
        lit = int(round(self._fraction(level_db) * segments))
        for i in range(segments):
            x = rect.x() + i * (seg_w + gap)
            db = -60.0 + (i / max(1, segments - 1)) * 60.0
            color = self._segment_color(db, i < lit)
            if i < lit and alpha < 1.0:
                color.setAlphaF(alpha)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, rect.y(), max(1.0, seg_w), rect.height()), 1.0, 1.0)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        full = self.rect().adjusted(14, 1, -8, -2)
        scale_h = 16
        meter_top = full.top() + scale_h
        meter_width = full.width()

        # Scale labels and calibration ticks.
        font = QFont(self.font())
        font.setPixelSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#8CA3B9"))
        for db in self.SCALE:
            frac = self._fraction(float(db))
            x = full.left() + meter_width * frac
            text = str(db)
            tw = painter.fontMetrics().horizontalAdvance(text)
            painter.drawText(int(x - tw / 2), int(full.top() + 9), text)
            painter.setPen(QPen(QColor("#38546D"), 1))
            painter.drawLine(QPointF(x, meter_top - 1), QPointF(x, meter_top + 3))
            painter.setPen(QColor("#8CA3B9"))

        peak_rect = QRectF(full.left(), meter_top + 3, meter_width, 12)
        rms_rect = QRectF(full.left(), meter_top + 19, meter_width, 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#07131F"))
        painter.drawRoundedRect(peak_rect.adjusted(-1, -1, 1, 1), 3, 3)
        painter.drawRoundedRect(rms_rect.adjusted(-1, -1, 1, 1), 3, 3)
        self._draw_bar(painter, peak_rect, self._level_db, 1.0)
        self._draw_bar(painter, rms_rect, self._rms_db, 0.78)

        peak_x = peak_rect.left() + peak_rect.width() * self._fraction(self._peak_db)
        painter.setPen(QPen(QColor("#F8FBFF"), 2))
        painter.drawLine(QPointF(peak_x, peak_rect.top() - 2), QPointF(peak_x, rms_rect.bottom() + 1))

        if time.monotonic() < self._clipped_until:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FF3344"))
            painter.drawRoundedRect(QRectF(full.right() - 5, peak_rect.top(), 5, rms_rect.bottom() - peak_rect.top()), 2, 2)
        painter.end()


class WaveformWidget(QWidget):
    """Compact production waveform with playback playhead and click/drag scrubbing."""

    seekRequested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mins: list[float] = []
        self._maxs: list[float] = []
        self._duration = 0.0
        self._position = 0.0
        self._loading = False
        self.setObjectName("WaveformWidget")
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click or drag across the waveform to scrub playback.")
        self.setMouseTracking(True)

    def clear(self) -> None:
        self._mins = []
        self._maxs = []
        self._duration = 0.0
        self._position = 0.0
        self._loading = False
        self.update()

    def set_loading(self, loading: bool = True) -> None:
        self._loading = bool(loading)
        self.update()

    def set_waveform(self, mins: list[float], maxs: list[float], duration: float) -> None:
        self._mins = [float(v) for v in mins]
        self._maxs = [float(v) for v in maxs]
        self._duration = max(0.0, float(duration))
        self._position = min(self._position, self._duration)
        self._loading = False
        self.update()

    def set_position(self, seconds: float) -> None:
        value = max(0.0, float(seconds))
        if self._duration > 0:
            value = min(value, self._duration)
        if abs(value - self._position) > 0.005:
            self._position = value
            self.update()

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def position(self) -> float:
        return self._position


    def _seconds_at_x(self, x: float) -> float:
        if self._duration <= 0:
            return 0.0
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        inner = rect.adjusted(12, 12, -12, -12)
        if inner.width() <= 0:
            return 0.0
        frac = max(0.0, min(1.0, (float(x) - inner.left()) / inner.width()))
        return frac * self._duration

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._duration > 0 and self._mins:
            seconds = self._seconds_at_x(event.position().x())
            self.set_position(seconds)
            self.seekRequested.emit(seconds)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton and self._duration > 0 and self._mins:
            seconds = self._seconds_at_x(event.position().x())
            self.set_position(seconds)
            self.seekRequested.emit(seconds)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor("#06111B"))
        painter.setPen(QPen(QColor("#173047"), 1))
        painter.drawRoundedRect(rect, 7, 7)

        inner = rect.adjusted(12, 12, -12, -12)
        mid = inner.center().y()
        painter.setPen(QPen(QColor("#183249"), 1))
        painter.drawLine(QPointF(inner.left(), mid), QPointF(inner.right(), mid))
        for frac in (0.25, 0.5, 0.75):
            x = inner.left() + inner.width() * frac
            painter.setPen(QPen(QColor("#10283C"), 1))
            painter.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))

        if self._loading:
            painter.setPen(QColor("#7E9AB5"))
            painter.drawText(inner.toRect(), Qt.AlignCenter, "BUILDING WAVEFORM…")
            painter.end()
            return

        count = min(len(self._mins), len(self._maxs))
        if count <= 0:
            painter.setPen(QColor("#657D93"))
            painter.drawText(inner.toRect(), Qt.AlignCenter, "SELECT A TAKE TO VIEW WAVEFORM")
            painter.end()
            return

        half = inner.height() * 0.44
        painter.setPen(QPen(QColor("#36A8FF"), 1))
        step = inner.width() / max(1, count - 1)
        for i in range(count):
            x = inner.left() + i * step
            lo = max(-1.0, min(1.0, self._mins[i]))
            hi = max(-1.0, min(1.0, self._maxs[i]))
            y1 = mid - hi * half
            y2 = mid - lo * half
            if abs(y2 - y1) < 1.0:
                y2 = y1 + 1.0
            painter.drawLine(QPointF(x, y1), QPointF(x, y2))

        if self._duration > 0:
            frac = max(0.0, min(1.0, self._position / self._duration))
            px = inner.left() + inner.width() * frac
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.drawLine(QPointF(px, inner.top()), QPointF(px, inner.bottom()))
            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(px, inner.top() + 3), 3, 3)

        painter.end()


class TrackRow(QFrame):
    armedChanged = Signal(int, bool)
    nameChanged = Signal(int, str)
    sourceChanged = Signal(int, int)

    def __init__(self, channel_index: int, name: str, parent=None):
        super().__init__(parent)
        self.channel_index = channel_index
        self.setObjectName("TrackRow")
        self.setMinimumHeight(76)
        self.setMaximumHeight(84)

        row = QHBoxLayout(self)
        row.setContentsMargins(7, 5, 10, 5)
        row.setSpacing(9)

        accent = QFrame()
        accent.setObjectName("TrackAccent")
        accents = ["#168BFF", "#9A4DFF", "#11D5C5", "#FF7A22", "#E84F8A", "#54C46F"]
        accent.setStyleSheet(f"background:{accents[channel_index % len(accents)]}; border:0; border-radius:2px;")
        accent.setFixedSize(5, 54)
        row.addWidget(accent)

        self.channel_label = QLabel(f"{channel_index + 1:02d}")
        self.channel_label.setObjectName("ChannelNumber")
        self.channel_label.setAlignment(Qt.AlignCenter)
        self.channel_label.setFixedWidth(35)
        row.addWidget(self.channel_label)

        identity = QWidget()
        identity.setObjectName("TrackIdentity")
        ident_l = QVBoxLayout(identity)
        ident_l.setContentsMargins(0, 0, 0, 0)
        ident_l.setSpacing(2)
        self.name_edit = QLineEdit(name)
        self.name_edit.setObjectName("TrackName")
        self.name_edit.setMinimumWidth(108)
        self.name_edit.setMaximumWidth(150)
        self.name_edit.editingFinished.connect(
            lambda: self.nameChanged.emit(self.channel_index, self.name_edit.text().strip())
        )
        ident_l.addWidget(self.name_edit)

        self.arm_button = QPushButton()
        self.arm_button.setObjectName("ArmButton")
        self.arm_button.setCheckable(True)
        self.arm_button.setChecked(True)
        self.arm_button.setFixedSize(76, 24)
        self.arm_button.setToolTip(
            "Record-enable this input. REC means its audio is written to the take; "
            "OFF means the input stays visible on the meter but is written as silence."
        )
        self.arm_button.toggled.connect(self._arm_state_changed)
        self._update_arm_button(True)
        identity_footer = QHBoxLayout()
        identity_footer.setContentsMargins(0, 0, 0, 0)
        identity_footer.setSpacing(6)
        identity_footer.addWidget(self.arm_button)
        self.source_combo = DeviceComboBox()
        self.source_combo.setObjectName("TrackSourceCombo")
        self.source_combo.setFixedWidth(88)
        self.source_combo.setMinimumHeight(24)
        self.source_combo.setToolTip("Choose the physical interface input routed to this ISO track")
        self.source_combo.currentIndexChanged.connect(self._source_state_changed)
        identity_footer.addWidget(self.source_combo)
        identity_footer.addStretch(1)
        ident_l.addLayout(identity_footer)
        row.addWidget(identity)

        self.meter = PeakMeter()
        row.addWidget(self.meter, 1)

        values = QWidget()
        values.setObjectName("MeterReadouts")
        vg = QGridLayout(values)
        vg.setContentsMargins(0, 0, 0, 0)
        vg.setHorizontalSpacing(12)
        vg.setVerticalSpacing(0)
        peak_title = QLabel("PEAK")
        peak_title.setObjectName("MeterLabel")
        rms_title = QLabel("RMS")
        rms_title.setObjectName("MeterLabel")
        self.db_label = QLabel("-inf dB")
        self.db_label.setObjectName("MeterValue")
        self.rms_label = QLabel("-inf dB")
        self.rms_label.setObjectName("MeterValueSecondary")
        for lab in (peak_title, rms_title, self.db_label, self.rms_label):
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vg.addWidget(peak_title, 0, 0)
        vg.addWidget(rms_title, 0, 1)
        vg.addWidget(self.db_label, 1, 0)
        vg.addWidget(self.rms_label, 1, 1)
        values.setFixedWidth(134)
        row.addWidget(values)

        self.clip_label = QLabel("CLIP")
        self.clip_label.setObjectName("ClipBadge")
        self.clip_label.setAlignment(Qt.AlignCenter)
        self.clip_label.setFixedWidth(38)
        self.clip_label.setVisible(False)
        row.addWidget(self.clip_label)

    def _update_arm_button(self, armed: bool) -> None:
        self.arm_button.setText("REC" if armed else "OFF")
        self.arm_button.setIcon(make_icon("record", 40) if armed else QIcon())
        self.arm_button.setIconSize(QSize(10, 10))
        self.arm_button.setProperty("recordState", "armed" if armed else "off")
        self.arm_button.setAccessibleName(
            f"Track {self.channel_index + 1} record enabled" if armed
            else f"Track {self.channel_index + 1} record disabled"
        )
        self.arm_button.style().unpolish(self.arm_button)
        self.arm_button.style().polish(self.arm_button)
        self.arm_button.update()

    def _arm_state_changed(self, armed: bool) -> None:
        self._update_arm_button(armed)
        self.armedChanged.emit(self.channel_index, armed)

    @staticmethod
    def _format_db(db: float) -> str:
        if db <= -79.0 or not math.isfinite(db):
            return "-inf dB"
        return f"{db:.1f} dB"

    def set_level(self, db: float, rms_db: float | None = None) -> None:
        rms_db = db if rms_db is None else rms_db
        self.meter.set_level(db, rms_db)
        self.db_label.setText(self._format_db(db))
        self.rms_label.setText(self._format_db(rms_db))
        self.clip_label.setVisible(db >= -0.1)

    def set_source_options(self, options: list[tuple[str, int]], current: int = 0) -> None:
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        for label, value in options:
            self.source_combo.addItem(str(label), int(value))
        found = self.source_combo.findData(int(current))
        self.source_combo.setCurrentIndex(found if found >= 0 else (0 if self.source_combo.count() else -1))
        self.source_combo.setEnabled(self.source_combo.count() > 1)
        self.source_combo.blockSignals(False)

    def set_source(self, source: int) -> None:
        found = self.source_combo.findData(int(source))
        if found >= 0 and found != self.source_combo.currentIndex():
            self.source_combo.blockSignals(True)
            self.source_combo.setCurrentIndex(found)
            self.source_combo.blockSignals(False)

    def set_source_label(self, text: str) -> None:
        # Compatibility shim for older callers; the authoritative control is now the combo.
        if self.source_combo.count() == 0:
            self.source_combo.addItem(str(text), self.channel_index)

    def _source_state_changed(self, _index: int) -> None:
        data = self.source_combo.currentData()
        if data is not None:
            self.sourceChanged.emit(self.channel_index, int(data))

    def set_locked(self, locked: bool) -> None:
        self.arm_button.setEnabled(not locked)
        self.source_combo.setEnabled((not locked) and self.source_combo.count() > 1)
        self.name_edit.setReadOnly(locked)

    def is_armed(self) -> bool:
        return self.arm_button.isChecked()

    def track_name(self) -> str:
        return self.name_edit.text().strip() or f"Input {self.channel_index + 1}"


class TransportControl(QWidget):
    """Circular transport control with an adjacent label and shortcut badge."""

    def __init__(
        self,
        label: str,
        icon: QIcon,
        role: str = "secondary",
        shortcut: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("TransportControl")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.button = QPushButton()
        self.button.setObjectName("TransportCircle")
        self.button.setProperty("role", role)
        size = 96 if role == "record" else 88
        self.button.setFixedSize(size, size)
        self.button.setIcon(icon)
        self.button.setIconSize(QSize(42 if role == "record" else 30, 42 if role == "record" else 30))
        self.button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.button)

        text = QVBoxLayout()
        text.setSpacing(4)
        self.label = QLabel(label)
        self.label.setObjectName("TransportLabel")
        text.addWidget(self.label)
        self.shortcut = QLabel(shortcut)
        self.shortcut.setObjectName("ShortcutBadge")
        self.shortcut.setAlignment(Qt.AlignCenter)
        self.shortcut.setFixedWidth(max(24, 11 + len(shortcut) * 7))
        self.shortcut.setVisible(bool(shortcut))
        text.addWidget(self.shortcut, 0, Qt.AlignLeft)
        text.addStretch(1)
        layout.addLayout(text)
        layout.addStretch(1)

    def set_label(self, label: str) -> None:
        self.label.setText(label)


class TransportButton(QPushButton):
    """Legacy rectangular transport button retained for compatibility."""

    def __init__(self, text: str, role: str = "secondary", icon: QIcon | None = None, parent=None):
        super().__init__(text, parent)
        self.setProperty("role", role)
        self.setMinimumHeight(64)
        if icon is not None and not icon.isNull():
            self.setIcon(icon)
            self.setIconSize(QSize(28, 28))
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(11)
        self.setFont(font)
