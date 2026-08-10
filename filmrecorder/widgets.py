from __future__ import annotations

import math
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


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


class StatusPill(QLabel):
    def __init__(self, text: str = "", tone: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(30)
        self.setContentsMargins(12, 0, 12, 0)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)


class PeakMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level_db = -80.0
        self._peak_db = -80.0
        self._peak_time = 0.0
        self._clipped_until = 0.0
        self.setMinimumHeight(24)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @property
    def level_db(self) -> float:
        return self._level_db

    def set_level(self, db: float) -> None:
        db = max(-80.0, min(3.0, float(db)))
        self._level_db = db
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
        self._peak_time = 0.0
        self._clipped_until = 0.0
        self.update()

    @staticmethod
    def _fraction(db: float) -> float:
        db = max(-60.0, min(0.0, db))
        return (db + 60.0) / 60.0

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 3, 0, -3)
        radius = 5.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#0A1018"))
        painter.drawRoundedRect(rect, radius, radius)

        level_fraction = self._fraction(self._level_db)
        fill_width = int(rect.width() * level_fraction)
        if fill_width > 0:
            green_end = int(rect.width() * self._fraction(-12.0))
            amber_end = int(rect.width() * self._fraction(-6.0))
            painter.save()
            painter.setClipRect(rect.x(), rect.y(), fill_width, rect.height())
            painter.setBrush(QColor("#38D39F"))
            painter.drawRoundedRect(rect, radius, radius)
            if fill_width > green_end:
                painter.setBrush(QColor("#F6C85F"))
                painter.drawRect(rect.x() + green_end, rect.y(), max(0, fill_width - green_end), rect.height())
            if fill_width > amber_end:
                painter.setBrush(QColor("#FF5D73"))
                painter.drawRect(rect.x() + amber_end, rect.y(), max(0, fill_width - amber_end), rect.height())
            painter.restore()

        peak_x = rect.x() + int(rect.width() * self._fraction(self._peak_db))
        painter.setPen(QPen(QColor("#E8EEF5"), 2))
        painter.drawLine(peak_x, rect.y() + 2, peak_x, rect.bottom() - 2)

        if time.monotonic() < self._clipped_until:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FF3B5C"))
            painter.drawRoundedRect(rect.right() - 7, rect.y(), 7, rect.height(), 3, 3)

        painter.setPen(QPen(QColor("#314154"), 1))
        for db in (-48, -24, -12, -6):
            x = rect.x() + int(rect.width() * self._fraction(float(db)))
            painter.drawLine(x, rect.bottom() - 4, x, rect.bottom())


class TrackRow(QFrame):
    armedChanged = Signal(int, bool)
    nameChanged = Signal(int, str)

    def __init__(self, channel_index: int, name: str, parent=None):
        super().__init__(parent)
        self.channel_index = channel_index
        self.setObjectName("TrackRow")
        self.setMinimumHeight(62)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)

        self.channel_label = QLabel(f"{channel_index + 1:02d}")
        self.channel_label.setObjectName("ChannelNumber")
        self.channel_label.setFixedWidth(34)
        row.addWidget(self.channel_label)

        self.arm_button = QPushButton("ARM")
        self.arm_button.setObjectName("ArmButton")
        self.arm_button.setCheckable(True)
        self.arm_button.setChecked(True)
        self.arm_button.setFixedWidth(58)
        self.arm_button.toggled.connect(lambda value: self.armedChanged.emit(self.channel_index, value))
        row.addWidget(self.arm_button)

        self.name_edit = QLineEdit(name)
        self.name_edit.setObjectName("TrackName")
        self.name_edit.setFixedWidth(150)
        self.name_edit.editingFinished.connect(
            lambda: self.nameChanged.emit(self.channel_index, self.name_edit.text().strip())
        )
        row.addWidget(self.name_edit)

        self.meter = PeakMeter()
        row.addWidget(self.meter, 1)

        self.db_label = QLabel("-inf")
        self.db_label.setObjectName("DbReadout")
        self.db_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.db_label.setFixedWidth(62)
        row.addWidget(self.db_label)

        self.clip_label = QLabel("CLIP")
        self.clip_label.setObjectName("ClipBadge")
        self.clip_label.setAlignment(Qt.AlignCenter)
        self.clip_label.setFixedWidth(42)
        self.clip_label.setVisible(False)
        row.addWidget(self.clip_label)

    def set_level(self, db: float) -> None:
        self.meter.set_level(db)
        if db <= -79.0 or not math.isfinite(db):
            self.db_label.setText("-inf")
        else:
            self.db_label.setText(f"{db:5.1f}")
        self.clip_label.setVisible(db >= -0.1)

    def set_locked(self, locked: bool) -> None:
        self.arm_button.setEnabled(not locked)
        self.name_edit.setReadOnly(locked)

    def is_armed(self) -> bool:
        return self.arm_button.isChecked()

    def track_name(self) -> str:
        return self.name_edit.text().strip() or f"Input {self.channel_index + 1}"


class TransportButton(QPushButton):
    def __init__(self, text: str, role: str = "secondary", parent=None):
        super().__init__(text, parent)
        self.setProperty("role", role)
        self.setMinimumHeight(64)
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(11)
        self.setFont(font)
