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
        self.setMinimumHeight(34)
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
        rect = self.rect().adjusted(1, 4, -1, -5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#06111B"))
        painter.drawRoundedRect(rect, 4, 4)

        # Segmented meter reads as instrumentation rather than a progress bar.
        segments = 72
        gap = 2
        usable = max(1, rect.width() - gap * (segments - 1))
        seg_w = max(1, usable / segments)
        lit = int(round(self._fraction(self._level_db) * segments))
        for i in range(segments):
            x = rect.x() + i * (seg_w + gap)
            db = -60.0 + (i / max(1, segments - 1)) * 60.0
            if i < lit:
                if db < -18:
                    color = QColor("#08D9C4")
                elif db < -12:
                    color = QColor("#38E85B")
                elif db < -6:
                    color = QColor("#D7E91A")
                elif db < -3:
                    color = QColor("#FFC928")
                else:
                    color = QColor("#FF4A42")
            else:
                color = QColor("#10263A")
            painter.setBrush(color)
            painter.drawRoundedRect(int(x), rect.y()+4, max(1,int(seg_w)), max(3,rect.height()-8), 1, 1)

        peak_x = rect.x() + int(rect.width() * self._fraction(self._peak_db))
        painter.setPen(QPen(QColor("#F7FBFF"), 2))
        painter.drawLine(peak_x, rect.y()+2, peak_x, rect.bottom()-2)

        if time.monotonic() < self._clipped_until:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FF3344"))
            painter.drawRoundedRect(rect.right()-7, rect.y(), 7, rect.height(), 2, 2)

        painter.setPen(QPen(QColor("#42627C"), 1))
        for db in (-48, -36, -24, -18, -12, -6, -3):
            x = rect.x() + int(rect.width() * self._fraction(float(db)))
            painter.drawLine(x, rect.bottom()-3, x, rect.bottom())


class TrackRow(QFrame):
    armedChanged = Signal(int, bool)
    nameChanged = Signal(int, str)

    def __init__(self, channel_index: int, name: str, parent=None):
        super().__init__(parent)
        self.channel_index = channel_index
        self.setObjectName("TrackRow")
        self.setMinimumHeight(58)

        row = QHBoxLayout(self)
        row.setContentsMargins(9, 6, 9, 6)
        row.setSpacing(7)

        self.channel_label = QLabel(f"{channel_index + 1:02d}")
        self.channel_label.setObjectName("ChannelNumber")
        accents = ["#168BFF", "#9A4DFF", "#11D5C5", "#FF7A22"]
        accent = accents[channel_index % len(accents)]
        self.channel_label.setStyleSheet(f"border-left: 4px solid {accent}; padding-left: 7px;")
        self.channel_label.setFixedWidth(40)
        row.addWidget(self.channel_label)

        self.arm_button = QPushButton("ARM")
        self.arm_button.setObjectName("ArmButton")
        self.arm_button.setCheckable(True)
        self.arm_button.setChecked(True)
        self.arm_button.setFixedWidth(52)
        self.arm_button.toggled.connect(lambda value: self.armedChanged.emit(self.channel_index, value))
        row.addWidget(self.arm_button)

        self.name_edit = QLineEdit(name)
        self.name_edit.setObjectName("TrackName")
        self.name_edit.setMinimumWidth(92)
        self.name_edit.setMaximumWidth(180)
        self.name_edit.editingFinished.connect(
            lambda: self.nameChanged.emit(self.channel_index, self.name_edit.text().strip())
        )
        row.addWidget(self.name_edit)

        self.meter = PeakMeter()
        row.addWidget(self.meter, 1)

        self.db_label = QLabel("-inf")
        self.db_label.setObjectName("DbReadout")
        self.db_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.db_label.setFixedWidth(54)
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
