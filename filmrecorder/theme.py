from __future__ import annotations

APP_STYLESHEET = r"""
QWidget {
    background: #0B1118;
    color: #EAF0F6;
    font-family: "Segoe UI", "SF Pro Text", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background: #080D13;
}

QMenuBar {
    background: #080D13;
    border-bottom: 1px solid #1B2734;
}

QMenuBar::item {
    padding: 7px 10px;
    background: transparent;
}

QMenuBar::item:selected {
    background: #182230;
    border-radius: 5px;
}

QMenu {
    background: #111923;
    border: 1px solid #263547;
    padding: 6px;
}

QMenu::item {
    padding: 7px 28px 7px 10px;
    border-radius: 5px;
}

QMenu::item:selected {
    background: #1F3041;
}

QFrame#Card {
    background: #111923;
    border: 1px solid #1F2C3A;
    border-radius: 12px;
}

QLabel#CardTitle {
    color: #F7FAFC;
    font-size: 15px;
    font-weight: 700;
    background: transparent;
}

QLabel#CardSubtitle {
    color: #7F91A4;
    font-size: 11px;
    background: transparent;
}

QLabel#AppTitle {
    color: #F8FBFF;
    font-size: 22px;
    font-weight: 800;
    background: transparent;
}

QLabel#AppSubtitle, QLabel#Muted, QLabel#FieldLabel {
    color: #8394A7;
    background: transparent;
}

QLabel#FieldLabel {
    font-size: 11px;
    font-weight: 600;
}

QLabel#RecordClock {
    color: #F7FAFC;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 37px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}

QLabel#TakePreview {
    color: #98A8B9;
    font-family: "Cascadia Mono", "Consolas", monospace;
    background: transparent;
}

QLabel#StatusText {
    color: #9AA9B8;
    background: transparent;
}

QLabel[tone="neutral"] {
    background: #17212C;
    color: #AEBCC9;
    border: 1px solid #253445;
    border-radius: 15px;
    font-weight: 700;
}

QLabel[tone="ready"] {
    background: #103126;
    color: #6DE1B4;
    border: 1px solid #1C654A;
    border-radius: 15px;
    font-weight: 700;
}

QLabel[tone="recording"] {
    background: #3A101A;
    color: #FF8092;
    border: 1px solid #7C2637;
    border-radius: 15px;
    font-weight: 800;
}

QLabel[tone="warning"] {
    background: #3A2A0D;
    color: #F7C760;
    border: 1px solid #6A4B17;
    border-radius: 15px;
    font-weight: 700;
}

QLabel[tone="danger"] {
    background: #3A101A;
    color: #FF8092;
    border: 1px solid #7C2637;
    border-radius: 15px;
    font-weight: 700;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
    background: #0C141E;
    color: #EFF4F9;
    border: 1px solid #263648;
    border-radius: 7px;
    padding: 7px 9px;
    selection-background-color: #20678D;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border: 1px solid #3BAEEA;
}

QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QTextEdit:disabled {
    color: #657688;
    background: #0B121A;
}

QComboBox::drop-down {
    border: 0;
    width: 24px;
}

QComboBox QAbstractItemView {
    background: #111923;
    color: #EAF0F6;
    border: 1px solid #2A3A4C;
    selection-background-color: #1F4C67;
}

QPushButton {
    background: #17222F;
    color: #EAF0F6;
    border: 1px solid #2B3A4A;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background: #1D2B3A;
    border-color: #3A4D61;
}

QPushButton:pressed {
    background: #111923;
}

QPushButton:disabled {
    color: #5D6A78;
    background: #111820;
    border-color: #1D2732;
}

QPushButton[role="record"] {
    background: #D92546;
    color: white;
    border: 1px solid #F04464;
    border-radius: 10px;
}

QPushButton[role="record"]:hover {
    background: #EB3154;
}

QPushButton[role="stop"] {
    background: #233041;
    color: #FFFFFF;
    border: 1px solid #3B4D61;
    border-radius: 10px;
}

QPushButton[role="accent"] {
    background: #123C53;
    color: #79D4FF;
    border: 1px solid #246C8C;
    border-radius: 10px;
}

QPushButton[role="circle"]:checked {
    background: #4A3410;
    color: #FFD16A;
    border: 1px solid #8A6321;
}

QPushButton#ArmButton {
    background: #12201C;
    color: #6B8C80;
    border: 1px solid #234135;
    border-radius: 6px;
    padding: 5px;
}

QPushButton#ArmButton:checked {
    background: #12372A;
    color: #69E4B2;
    border: 1px solid #227552;
}

QFrame#TrackRow {
    background: #0D151F;
    border: 1px solid #1D2A37;
    border-radius: 9px;
}

QLabel#ChannelNumber {
    color: #708194;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-weight: 700;
    background: transparent;
}

QLineEdit#TrackName {
    background: transparent;
    border: 1px solid transparent;
    padding: 5px 6px;
    font-weight: 700;
}

QLineEdit#TrackName:focus {
    background: #0A121B;
    border: 1px solid #31526C;
}

QLabel#DbReadout {
    color: #C6D1DC;
    font-family: "Cascadia Mono", "Consolas", monospace;
    background: transparent;
}

QLabel#ClipBadge {
    background: #5A1420;
    color: #FF8B9B;
    border: 1px solid #932D40;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 800;
}

QCheckBox {
    spacing: 8px;
    color: #C5D0DA;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3A4A5D;
    border-radius: 4px;
    background: #0C141E;
}

QCheckBox::indicator:checked {
    background: #2D8CBF;
    border: 1px solid #59C0F2;
}

QScrollArea {
    border: 0;
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #314154;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QSplitter::handle {
    background: transparent;
    width: 8px;
}

QToolTip {
    background: #182230;
    color: #F2F6FA;
    border: 1px solid #33485D;
    padding: 6px;
}
"""

# Responsive/laptop-density additions for v0.3.1
APP_STYLESHEET += r"""
QTabWidget::pane {
    border: 1px solid #1F2C3A;
    border-radius: 10px;
    background: #0D141D;
    top: -1px;
}

QTabBar::tab {
    background: #101923;
    color: #8192A4;
    border: 1px solid #1F2C3A;
    border-bottom: 0;
    padding: 9px 13px;
    min-width: 54px;
    font-weight: 700;
}

QTabBar::tab:first {
    border-top-left-radius: 8px;
}

QTabBar::tab:last {
    border-top-right-radius: 8px;
}

QTabBar::tab:selected {
    background: #172432;
    color: #EAF0F6;
    border-color: #31516A;
}

QTabBar::tab:hover:!selected {
    background: #14202C;
    color: #C8D3DE;
}

QFrame#TransportCard {
    background: #0E1721;
    border: 1px solid #2A3949;
    border-radius: 12px;
}
"""
