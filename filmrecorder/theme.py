from __future__ import annotations

# FilmSet Recorder v0.5 visual system
# Restrained, instrument-like, low-chrome UI inspired by production sound
# hardware and professional nonlinear editing applications.
APP_STYLESHEET = r"""
QWidget {
    background: #0B0D10;
    color: #E7EAEE;
    font-family: "Inter", "SF Pro Text", "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}

QMainWindow, QWidget#AppRoot { background: #090B0D; }

QMenuBar {
    background: #090B0D;
    color: #B7BEC7;
    border-bottom: 1px solid #1A1E23;
    padding: 1px 4px;
}
QMenuBar::item { background: transparent; padding: 5px 9px; }
QMenuBar::item:selected { background: #171B20; color: #F4F6F8; }
QMenu { background: #111419; border: 1px solid #2A3037; padding: 5px; }
QMenu::item { padding: 7px 28px 7px 10px; }
QMenu::item:selected { background: #242A31; }

QFrame#Card {
    background: #101318;
    border: 1px solid #22272E;
    border-radius: 5px;
}
QFrame#SlateStrip {
    background: #0E1115;
    border: 1px solid #252A31;
    border-radius: 4px;
}
QFrame#ConsoleSurface {
    background: #0D1014;
    border: 1px solid #242A31;
    border-radius: 4px;
}
QFrame#TransportBar {
    background: #0E1115;
    border-top: 1px solid #2A3037;
    border-left: 0;
    border-right: 0;
    border-bottom: 0;
    border-radius: 0;
}

QLabel#CardTitle, QLabel#SectionTitle {
    color: #EEF1F4;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#CardSubtitle, QLabel#SectionMeta {
    color: #6F7883;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#AppTitle {
    color: #F3F5F7;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#AppSubtitle {
    color: #737D88;
    font-size: 11px;
    background: transparent;
}
QLabel#FormatReadout {
    color: #89939E;
    font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
    font-size: 10px;
    background: transparent;
}
QLabel#FieldLabel {
    color: #737D88;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#Muted { color: #727C87; font-size: 10px; background: transparent; }
QLabel#FilePreview, QLabel#NetworkAddress, QLabel#TransportSlate {
    color: #B7BFC8;
    font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
    font-size: 11px;
    background: transparent;
}
QLabel#PairingCode {
    color: #E6E9ED;
    font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 2px;
    background: transparent;
}
QLabel#RecordClock {
    color: #F2F4F6;
    font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
    font-size: 34px;
    font-weight: 650;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#StatusText { color: #8A949F; font-size: 10px; background: transparent; }
QLabel#MeterScale {
    color: #535D68;
    font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
    font-size: 8px;
    background: transparent;
}
QLabel#DiagnosticValue { color: #C3CAD2; font-family: "SF Mono", Consolas, monospace; }

/* Status indicators are deliberately compact, not decorative pills. */
QLabel[tone="neutral"], QLabel[tone="ready"], QLabel[tone="recording"],
QLabel[tone="warning"], QLabel[tone="danger"] {
    background: transparent;
    border: 0;
    border-left: 3px solid #4B535D;
    border-radius: 0;
    padding: 0 8px;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
}
QLabel[tone="neutral"] { color: #747E89; border-left-color: #48515B; }
QLabel[tone="ready"] { color: #A7C9B8; border-left-color: #48A779; }
QLabel[tone="recording"] { color: #FFB4B4; border-left-color: #E54B4B; }
QLabel[tone="warning"] { color: #D9BF88; border-left-color: #C7923E; }
QLabel[tone="danger"] { color: #FFAAAA; border-left-color: #E05252; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
    background: #0A0D10;
    color: #E4E7EA;
    border: 1px solid #2A3037;
    border-radius: 3px;
    padding: 6px 8px;
    selection-background-color: #385A73;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border-color: #687480;
    background: #0D1014;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QTextEdit:disabled {
    color: #5D6670;
    background: #0C0F12;
    border-color: #1E2328;
}
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox QAbstractItemView { background: #11151A; color: #E5E8EB; border: 1px solid #303740; selection-background-color: #2B333C; }

QPushButton {
    background: #15191E;
    color: #C7CDD4;
    border: 1px solid #30363E;
    border-radius: 3px;
    padding: 7px 10px;
    font-weight: 650;
}
QPushButton:hover { background: #1B2026; color: #F2F4F6; border-color: #444D57; }
QPushButton:pressed { background: #0F1216; }
QPushButton:disabled { color: #505862; background: #101318; border-color: #22272D; }
QPushButton[role="primary"], QPushButton[role="accent"] {
    background: #25333E;
    color: #E2EBF2;
    border-color: #425665;
}
QPushButton[role="primary"]:hover, QPushButton[role="accent"]:hover { background: #2D3E4B; }
QPushButton[role="record"] {
    background: #A9262B;
    color: #FFFFFF;
    border: 1px solid #D34046;
    border-radius: 4px;
    font-weight: 800;
}
QPushButton[role="record"]:hover { background: #C12C32; }
QPushButton[role="stop"] {
    background: #1A1F24;
    color: #F1F3F5;
    border: 1px solid #4A515A;
    border-radius: 4px;
    font-weight: 800;
}
QPushButton[role="circle"]:checked {
    background: #302913;
    color: #E8D18C;
    border-color: #75622A;
}

QCheckBox { color: #B8C0C8; spacing: 7px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #414951; background: #0B0E11; border-radius: 2px; }
QCheckBox::indicator:checked { background: #55715F; border-color: #728D7A; }

QTabWidget#InspectorTabs::pane { border: 1px solid #242A31; background: #0D1014; top: -1px; }
QTabBar::tab {
    background: #0A0D10;
    color: #69737D;
    border: 0;
    border-bottom: 2px solid transparent;
    padding: 9px 10px 7px;
    font-size: 10px;
    font-weight: 700;
}
QTabBar::tab:selected { color: #E5E8EB; border-bottom-color: #77828D; }
QTabBar::tab:hover { color: #B6BEC6; }

QScrollArea, QWidget#InspectorPage, QWidget#TrackContainer { background: transparent; border: 0; }
QScrollBar:vertical { background: #0B0E11; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #333A42; min-height: 26px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #171B20; }
QSplitter::handle:hover { background: #293038; }

QFrame#TrackRow {
    background: transparent;
    border: 0;
    border-bottom: 1px solid #1C2127;
    border-radius: 0;
}
QFrame#TrackRow:hover { background: #11151A; }
QLabel#ChannelNumber {
    color: #626C77;
    font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
    font-size: 10px;
    font-weight: 700;
    background: transparent;
}
QPushButton#ArmButton {
    background: transparent;
    color: #5C6670;
    border: 1px solid #30363D;
    padding: 4px 5px;
    font-size: 9px;
    font-weight: 800;
}
QPushButton#ArmButton:checked { color: #D5E0D9; background: #24332A; border-color: #4C7058; }
QLineEdit#TrackName {
    background: transparent;
    border: 1px solid transparent;
    color: #DCE0E4;
    font-size: 11px;
    font-weight: 700;
    padding: 4px;
}
QLineEdit#TrackName:focus { background: #0A0D10; border-color: #343B43; }
QLabel#DbReadout {
    color: #A6AFB8;
    font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
    font-size: 10px;
    background: transparent;
}
QLabel#ClipBadge {
    background: #A82930;
    color: white;
    border-radius: 2px;
    font-size: 8px;
    font-weight: 900;
}

QTableWidget#TakeTable {
    background: #0A0D10;
    alternate-background-color: #0D1014;
    color: #C8CED5;
    border: 1px solid #242A31;
    selection-background-color: #25313B;
    selection-color: #F5F6F7;
    outline: 0;
}
QHeaderView::section {
    background: #11151A;
    color: #707A84;
    border: 0;
    border-bottom: 1px solid #2A3037;
    padding: 7px 6px;
    font-size: 9px;
    font-weight: 800;
}
QTableCornerButton::section { background: #11151A; border: 0; }

QToolTip { background: #171B20; color: #E6E9EC; border: 1px solid #3A424B; padding: 5px; }
"""
