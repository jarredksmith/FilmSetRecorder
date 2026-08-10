from __future__ import annotations

# FilmSet Recorder v0.6 visual system
# Premium production-console styling: deep blue-black surfaces, restrained
# electric-blue interaction accents, signal-state color only where functional.
APP_STYLESHEET = r"""
QWidget {
    background: #07111C;
    color: #EAF2FA;
    font-family: "Inter", "SF Pro Text", "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}
QMainWindow, QWidget#AppRoot { background: #06101A; }
QWidget#AppBody {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #08131F, stop:0.55 #091522, stop:1 #06101A);
}
QMenuBar { background:#050D15; color:#A7B4C4; border-bottom:1px solid #152639; padding:2px 8px; }
QMenuBar::item { padding:6px 10px; background:transparent; }
QMenuBar::item:selected { background:#102033; color:#FFFFFF; }
QMenu { background:#0B1622; border:1px solid #24384E; padding:5px; }
QMenu::item { padding:7px 30px 7px 12px; }
QMenu::item:selected { background:#17304C; }

QWidget#NavRail { background:#050D16; border-right:1px solid #16304A; }
QLabel#LogoMark { color:#2D8CFF; font-size:31px; font-weight:900; background:transparent; }
QLabel#BrandWave { color:#3797FF; font-size:18px; font-weight:900; background:transparent; }
QLabel#NavHelp { color:#6F8298; font-size:10px; background:transparent; }
QPushButton#NavButton {
    background:transparent; color:#7D8CA0; border:1px solid transparent;
    border-radius:8px; padding:7px 3px; font-size:10px; font-weight:700;
}
QPushButton#NavButton:hover { background:#0B1C2D; color:#D9E8F6; }
QPushButton#NavButton:checked { background:#0B2B52; color:#F4FAFF; border-color:#1483FF; }

QLabel#AppTitle { color:#F5FAFF; font-size:17px; font-weight:750; letter-spacing:2px; background:transparent; }
QLabel#AppSubtitle { color:#7F91A5; font-size:11px; background:transparent; }
QLabel#FormatReadout { color:#7FA7CA; font-family:"SF Mono","Cascadia Mono",Consolas,monospace; font-size:10px; background:transparent; }
QLabel#WorkspaceTitle { color:#F1F6FB; font-size:22px; font-weight:750; letter-spacing:1px; background:transparent; }
QLabel#SectionTitle { color:#F2F7FB; font-size:13px; font-weight:800; letter-spacing:1px; background:transparent; }
QLabel#SectionMeta { color:#7390AB; font-size:10px; font-weight:700; letter-spacing:1px; background:transparent; }
QLabel#FieldLabel { color:#6E89A3; font-size:9px; font-weight:800; letter-spacing:1px; background:transparent; }
QLabel#FilePreview, QLabel#NetworkAddress, QLabel#TransportSlate {
    color:#B9D2E8; font-family:"SF Mono","Cascadia Mono",Consolas,monospace; font-size:11px; background:transparent;
}
QLabel#PairingCode { color:#F5FAFF; font-family:"SF Mono","Cascadia Mono",Consolas,monospace; font-size:22px; font-weight:800; letter-spacing:3px; background:transparent; }
QLabel#StatusText { color:#A2B2C3; font-size:11px; background:transparent; }
QLabel#HeroClock { color:#FFFFFF; font-family:"SF Mono","Cascadia Mono",Consolas,monospace; font-size:38px; font-weight:800; letter-spacing:1px; background:transparent; }
QLabel#TinyState, QLabel#MiniHealth { color:#72D69B; font-family:"SF Mono",Consolas,monospace; font-size:9px; font-weight:800; background:transparent; }
QLabel#DiagnosticValue { color:#C8D9E8; font-family:"SF Mono",Consolas,monospace; background:transparent; }

QFrame#SlatePanel, QFrame#MeterConsole, QFrame#RecorderPanel, QFrame#LastTakeStrip, QFrame#DiagnosticsPanel {
    background:rgba(12,27,42,218); border:1px solid #1B344B; border-radius:10px;
}
QFrame#TransportDeck { background:transparent; border:0; }
QFrame#LastTakeStrip { background:#081522; }
QSplitter::handle { background:#0D2031; }
QSplitter::handle:hover { background:#1B4262; }

QLabel[tone="neutral"], QLabel[tone="ready"], QLabel[tone="recording"], QLabel[tone="warning"], QLabel[tone="danger"] {
    background:#0A1724; border:1px solid #203C55; border-radius:8px; padding:7px 11px;
    font-size:9px; font-weight:800; letter-spacing:.5px;
}
QLabel[tone="neutral"] { color:#9FB1C3; }
QLabel[tone="ready"] { color:#73E6A7; border-color:#155D3A; background:#08291D; }
QLabel[tone="recording"] { color:#FF9C9C; border-color:#7B2930; background:#351015; }
QLabel[tone="warning"] { color:#FFD179; border-color:#775A24; }
QLabel[tone="danger"] { color:#FF9696; border-color:#8A3037; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
    background:#07131F; color:#EEF6FD; border:1px solid #253E56; border-radius:6px; padding:8px 10px;
    selection-background-color:#165F9F;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus { border-color:#1E91FF; background:#081827; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color:#617488; border-color:#162A3D; }
QComboBox::drop-down { border:0; width:26px; }
QComboBox QAbstractItemView { background:#0A1724; color:#EAF3FA; border:1px solid #29445E; selection-background-color:#143B60; }

QPushButton { background:#0E1D2B; color:#C9D7E4; border:1px solid #29435A; border-radius:7px; padding:8px 12px; font-weight:700; }
QPushButton:hover { background:#132A3F; color:#FFFFFF; border-color:#3C6688; }
QPushButton:pressed { background:#091521; }
QPushButton:disabled { color:#526579; border-color:#172A3B; background:#0A1621; }
QPushButton[role="primary"] { background:#0B477A; color:#F4FAFF; border-color:#197BC6; }
QPushButton[role="primary"]:hover { background:#0D5796; border-color:#2E9CFF; }

QPushButton[role="record"], QPushButton[role="stop"], QPushButton[role="circle"], QPushButton[role="secondary"] {
    min-width:110px; border-radius:14px; font-size:11px; font-weight:850; padding:12px 12px;
}
QPushButton[role="record"] { background:#E62232; border:1px solid #FF5661; color:#FFFFFF; }
QPushButton[role="record"]:hover { background:#FF293B; }
QPushButton[role="stop"] { background:#101F2E; border:1px solid #36526C; color:#E8F1F8; }
QPushButton[role="secondary"] { background:#0C1B29; border:1px solid #29445E; color:#E0EAF3; }
QPushButton[role="circle"] { background:#0C1B29; border:1px solid #29445E; color:#E0EAF3; }
QPushButton[role="circle"]:checked { background:#4B3A0B; color:#FFD96A; border-color:#A77B18; }

QCheckBox { color:#B4C5D5; spacing:7px; }
QCheckBox::indicator { width:15px; height:15px; background:#07131F; border:1px solid #31506A; border-radius:3px; }
QCheckBox::indicator:checked { background:#1678D2; border-color:#2496FF; }

QScrollArea, QWidget#TrackContainer, QWidget#WorkspacePage, QWidget#RecordWorkspace { background:transparent; border:0; }
QScrollBar:vertical { background:#06111B; width:8px; }
QScrollBar::handle:vertical { background:#27445D; min-height:28px; border-radius:4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }

QFrame#TrackRow { background:#081522; border:1px solid #173047; border-radius:8px; }
QFrame#TrackRow:hover { background:#0A1B2A; border-color:#254A68; }
QLabel#ChannelNumber { color:#F1F6FA; font-family:"SF Mono",Consolas,monospace; font-size:12px; font-weight:800; background:transparent; }
QPushButton#ArmButton { background:#0A3826; color:#80F1AA; border:1px solid #157A4B; border-radius:6px; padding:5px 7px; font-size:9px; font-weight:900; }
QPushButton#ArmButton:checked { background:#0D522F; color:#B2FFCE; border-color:#1FA75E; }
QLineEdit#TrackName { background:transparent; border:1px solid transparent; color:#F0F5FA; font-size:12px; font-weight:800; padding:4px; }
QLineEdit#TrackName:focus { background:#07131F; border-color:#1E91FF; }
QLabel#DbReadout { color:#D5E2ED; font-family:"SF Mono",Consolas,monospace; font-size:10px; background:transparent; }
QLabel#ClipBadge { color:#FFF; background:#CB2635; border-radius:4px; font-size:8px; font-weight:900; }

QTableWidget#TakeTable { background:#081522; alternate-background-color:#0A1927; border:1px solid #1D3950; border-radius:8px; gridline-color:transparent; selection-background-color:#123F64; selection-color:#FFFFFF; }
QHeaderView::section { background:#0B1A28; color:#7994AE; border:0; border-bottom:1px solid #254159; padding:8px; font-size:9px; font-weight:800; }
QTableWidget::item { border-bottom:1px solid #142B3E; padding:7px; }

QTabWidget#WorkspaceTabs::pane { border:0; background:transparent; }
"""
