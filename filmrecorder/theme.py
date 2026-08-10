from __future__ import annotations

# FilmSet Recorder v0.7.0 visual system
# Closely follows the approved production-console mockup: layered navy surfaces,
# restrained cobalt accents, highly legible recorder typography, circular
# transport controls, and calibrated audio instrumentation.
APP_STYLESHEET = r"""
QWidget {
    background: #07111C;
    color: #EAF2FA;
    font-family: "Inter", "SF Pro Text", "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}
QMainWindow, QWidget#AppRoot { background: #050E17; }
QWidget#AppBody {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #091522, stop:0.5 #08131F, stop:1 #06101A);
}

/* Native menu chrome */
QMenuBar { background:#050C14; color:#A7B4C4; border-bottom:1px solid #142638; padding:2px 8px; }
QMenuBar::item { padding:6px 10px; background:transparent; }
QMenuBar::item:selected { background:#102033; color:#FFFFFF; }
QMenu { background:#0A1622; border:1px solid #24384E; padding:5px; }
QMenu::item { padding:7px 30px 7px 12px; }
QMenu::item:selected { background:#17304C; }

/* Left rail */
QWidget#NavRail { background:#050D16; border-right:1px solid #14283B; min-width:104px; max-width:104px; }
QLabel#LogoMark { background:transparent; border:0; }
QToolButton#NavButton {
    background:transparent; color:#8092A6; border:1px solid transparent;
    border-radius:9px; padding:6px 0px; font-size:10px; font-weight:650; text-align:center;
    min-width:84px; max-width:84px;
}
QToolButton#NavButton:hover { background:#0B1C2D; color:#E8F2FA; }
QToolButton#NavButton:checked {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0B315F, stop:1 #0A2343);
    color:#FFFFFF; border-color:#168BFF;
}
QToolButton#NavHelpButton { background:transparent; color:#71869B; border:0; padding:6px 2px; font-size:9px; }
QToolButton#NavHelpButton:hover { color:#FFFFFF; }

/* Brand/header */
QLabel#BrandWave, QLabel#SectionIcon { background:transparent; border:0; }
QLabel#ProductName { color:#F8FBFF; font-size:18px; font-weight:700; letter-spacing:3px; background:transparent; }
QLabel#ProductSub { color:#87A2BB; font-size:9px; font-weight:650; letter-spacing:4px; background:transparent; }
QFrame#HeaderDivider { color:#20384F; background:#20384F; border:0; max-width:1px; }
QLabel#ProjectTitle { color:#F5FAFF; font-size:18px; font-weight:750; background:transparent; }
QLabel#AppSubtitle { color:#758BA1; font-size:10px; background:transparent; }
QLabel#FormatReadout { color:#7DA6C9; font-family:"SF Mono","Cascadia Mono",Consolas,monospace; font-size:9px; font-weight:700; background:transparent; }
QToolButton#HeaderToolButton { background:transparent; border:0; border-left:1px solid #20384F; padding-left:12px; min-width:42px; }
QToolButton#HeaderToolButton:hover { background:#0D1F30; border-radius:8px; }

/* Status cards */
QFrame#StatusPill {
    background:#0A1724; border:1px solid #203B55; border-radius:8px;
    min-width:106px;
}
QFrame#StatusPill[tone="active"] { border-color:#24567A; background:#0A1D2E; }
QFrame#StatusPill[tone="ready"] { border-color:#145C3A; background:#08291D; }
QFrame#StatusPill[tone="recording"] { border-color:#8A2933; background:#3A1016; }
QFrame#StatusPill[tone="warning"] { border-color:#725621; background:#241D0A; }
QFrame#StatusPill[tone="danger"] { border-color:#89323A; background:#351117; }
QLabel#StatusPillIcon { background:transparent; border:0; }
QLabel#StatusPillText { background:transparent; color:#C2D0DE; font-size:9px; font-weight:850; letter-spacing:.4px; }
QLabel#StatusPillDetail { background:transparent; color:#91A4B7; font-size:9px; }
QFrame#StatusPill[tone="active"] QLabel#StatusPillText { color:#79C8FF; }
QFrame#StatusPill[tone="active"] QLabel#StatusPillDetail { color:#A7C6DE; }
QFrame#StatusPill[tone="ready"] QLabel#StatusPillText { color:#6CE7A4; }
QFrame#StatusPill[tone="ready"] QLabel#StatusPillDetail { color:#A8DCC1; }
QFrame#StatusPill[tone="recording"] QLabel#StatusPillText { color:#FF949D; }

/* Main workspaces */
QTabWidget#WorkspaceTabs::pane { border:0; background:transparent; }
QWidget#WorkspacePage, QWidget#RecordWorkspace, QWidget#TrackContainer, QScrollArea { background:transparent; border:0; }
QLabel#WorkspaceTitle { color:#F4F8FC; font-size:22px; font-weight:750; letter-spacing:1px; background:transparent; }
QLabel#SectionTitle { color:#F4F8FC; font-size:13px; font-weight:850; letter-spacing:1px; background:transparent; }
QLabel#SectionMeta { color:#7E9AB5; font-size:9px; font-weight:800; letter-spacing:.8px; background:transparent; }
QLabel#FieldLabel { color:#708BA5; font-size:8px; font-weight:850; letter-spacing:1px; background:transparent; }
QLabel#FilePreview, QLabel#NetworkAddress, QLabel#TransportSlate {
    color:#BCD2E6; font-family:"SF Mono","Cascadia Mono",Consolas,monospace; font-size:10px; background:transparent;
}
QLabel#PairingCode { color:#F5FAFF; font-family:"SF Mono","Cascadia Mono",Consolas,monospace; font-size:22px; font-weight:800; letter-spacing:3px; background:transparent; }

/* Layered console panels */
QFrame#SlatePanel, QFrame#MeterConsole, QFrame#RecorderPanel, QFrame#DiagnosticsPanel, QFrame#ProductionStrip {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(13,29,45,238), stop:1 rgba(9,23,37,238));
    border:1px solid #1A344C; border-radius:10px;
}
QFrame#SlatePanel { min-height:112px; }
QFrame#RecorderPanel { min-width:320px; }
QSplitter::handle { background:#0C1D2C; }
QSplitter::handle:hover { background:#1B4262; }

/* Slate */
QLineEdit#SlateField, QSpinBox#SlateField, QComboBox#SlateField {
    background:#07131F; color:#F7FBFF; border:1px solid #29445E; border-radius:7px;
    padding:7px 10px; font-size:18px; font-weight:750;
}
QLineEdit#SlateField:focus, QSpinBox#SlateField:focus, QComboBox#SlateField:focus {
    border-color:#1491FF; background:#081A2A;
}
QFrame#NextFileField { background:#081725; border:1px solid #243E56; border-radius:7px; }
QPushButton#SlateResetButton { min-height:34px; padding:7px 13px; }

/* Forms */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
    background:#07131F; color:#EEF6FD; border:1px solid #253E56; border-radius:6px; padding:8px 10px;
    selection-background-color:#165F9F;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus { border-color:#1E91FF; background:#081827; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color:#617488; border-color:#162A3D; }
QComboBox { padding-right:32px; }
QComboBox::drop-down { border:0; width:30px; }
QComboBox QAbstractItemView { background:#0A1724; color:#EAF3FA; border:1px solid #29445E; selection-background-color:#143B60; }
QComboBox#InputDeviceCombo, QComboBox#SystemInputDeviceCombo { border-color:#2E6C9F; background:#081A2A; font-weight:700; }

/* Standard buttons */
QPushButton { background:#0E1D2B; color:#C9D7E4; border:1px solid #29435A; border-radius:7px; padding:8px 12px; font-weight:700; }
QPushButton:hover { background:#132A3F; color:#FFFFFF; border-color:#3C6688; }
QPushButton:pressed { background:#091521; }
QPushButton:disabled { color:#526579; border-color:#172A3B; background:#0A1621; }
QPushButton[role="primary"] { background:#0B477A; color:#F4FAFF; border-color:#197BC6; }
QPushButton[role="primary"]:hover { background:#0D5796; border-color:#2E9CFF; }
QPushButton#QuickApplyButton { min-width:92px; }
QPushButton#AddNoteButton { min-height:34px; padding:7px 12px; }

/* ISO track console */
QFrame#TrackRow {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #081522, stop:1 #07131E);
    border:1px solid #173047; border-radius:8px;
}
QFrame#TrackRow:hover { background:#0A1B2A; border-color:#254A68; }
QLabel#ChannelNumber { color:#F2F7FB; font-family:"SF Mono",Consolas,monospace; font-size:13px; font-weight:850; background:transparent; }
QWidget#TrackIdentity, QWidget#MeterReadouts { background:transparent; }
QLineEdit#TrackName { background:transparent; border:1px solid transparent; color:#F0F5FA; font-size:12px; font-weight:850; padding:1px 2px; }
QLineEdit#TrackName:focus { background:#07131F; border-color:#1E91FF; }
QPushButton#ArmButton {
    background:#0A151F; color:#72869A; border:1px solid #2B4053; border-radius:5px;
    padding:2px 7px; font-size:8px; font-weight:900; letter-spacing:.5px;
}
QPushButton#ArmButton:checked { background:#3D1018; color:#FFD7DB; border-color:#D43A48; }
QPushButton#ArmButton:checked:hover { background:#57141E; border-color:#FF5A66; }
QPushButton#ArmButton:hover { background:#102130; color:#D5E2ED; }
QLabel#MeterLabel { color:#718AA1; font-size:7px; font-weight:800; letter-spacing:.5px; background:transparent; }
QLabel#MeterValue { color:#F3F8FC; font-family:"SF Mono",Consolas,monospace; font-size:10px; font-weight:700; background:transparent; }
QLabel#MeterValueSecondary { color:#AFC2D3; font-family:"SF Mono",Consolas,monospace; font-size:9px; background:transparent; }
QLabel#TrackSourceBadge { color:#7EA9C9; background:#0B1B29; border:1px solid #25445D; border-radius:4px; padding:2px 5px; font-size:7px; font-weight:800; }
QComboBox#TrackSourceCombo { min-height:24px; max-height:24px; padding:2px 22px 2px 7px; background:#081723; border:1px solid #285273; border-radius:4px; color:#9FD2F7; font-size:8px; font-weight:800; }
QComboBox#TrackSourceCombo:disabled { color:#72889A; border-color:#1B3448; background:#07131D; }
QComboBox#TrackSourceCombo::drop-down { width:20px; }
QLabel#ClipBadge { color:#FFF; background:#CB2635; border-radius:4px; font-size:8px; font-weight:900; }
QPushButton#AddInputButton {
    background:transparent; color:#6FAFE3; border:1px dashed #2A5579; border-radius:7px;
    padding:7px 12px; margin-top:4px; font-size:9px; font-weight:800; letter-spacing:.5px;
}
QPushButton#AddInputButton:hover { background:#0A2134; color:#BEE2FF; border-color:#168BFF; }

/* Recorder */
QFrame#ClockPanel { background:#06111B; border:1px solid #122B40; border-radius:7px; }
QLabel#HeroClock {
    color:#FFFFFF; font-family:"SF Mono","Cascadia Mono",Consolas,monospace;
    font-size:36px; font-weight:850; letter-spacing:1px; background:transparent;
}
QLabel#ClockUnit { color:#6F8AA4; font-size:7px; font-weight:800; letter-spacing:.5px; background:transparent; }
QLabel#RecorderStateBadge {
    background:#0C1823; color:#8194A8; border:1px solid #263C50; border-radius:14px;
    padding:5px 20px; font-size:10px; font-weight:850; letter-spacing:.5px;
}
QLabel#RecorderStateBadge[tone="ready"] { background:#09251B; color:#62E39B; border-color:#155F3B; }
QLabel#RecorderStateBadge[tone="recording"] { background:#4A111A; color:#FF9AA2; border-color:#A92A36; }
QLabel#RecorderStateBadge[tone="danger"] { background:#4A111A; color:#FF969D; border-color:#A92A36; }
QLabel#RecorderStateBadge[tone="playback"] { background:#0C2742; color:#86C7FF; border-color:#21547D; }
QFrame#RecorderHealth { background:#081724; border:1px solid #163047; border-radius:7px; }
QLabel#HealthDot { color:#24E782; font-size:10px; background:transparent; }
QLabel#HealthLabel { color:#8AA1B6; font-size:8px; background:transparent; }
QLabel#HealthValue { color:#F0F6FB; font-size:11px; font-weight:750; background:transparent; }
QLabel#TinyState { color:#72D69B; font-family:"SF Mono",Consolas,monospace; font-size:8px; font-weight:800; background:transparent; }

/* Circular transport, matching the mockup */
QFrame#TransportDeck { background:transparent; border:0; }
QWidget#TransportControl { background:transparent; }
QPushButton#TransportCircle {
    background:#0B1A29; border:1px solid #345878; border-radius:44px; padding:0;
}
QPushButton#TransportCircle:hover { background:#10263A; border-color:#5D8FB9; }
QPushButton#TransportCircle:pressed { background:#07131F; }
QPushButton#TransportCircle[role="record"] {
    background:qradialgradient(cx:.42,cy:.35,radius:.9,fx:.42,fy:.35, stop:0 #FF3C49, stop:.7 #E82030, stop:1 #A71320);
    border:1px solid #FF5E69; border-radius:48px;
}
QPushButton#TransportCircle[role="record"]:hover { background:#FF293B; border-color:#FF8A91; }
QPushButton#TransportCircle[role="circle"]:checked { background:#3A2B09; border-color:#B28724; }
QLabel#TransportLabel { color:#F1F6FA; font-size:11px; font-weight:800; background:transparent; }
QLabel#ShortcutBadge { color:#8499AD; background:#0B1927; border:1px solid #1C344B; border-radius:4px; padding:2px 4px; font-size:7px; }
QFrame#TransportDivider { color:#183249; background:#183249; border:0; max-width:1px; }

/* Production strip */
QFrame#ProductionStrip { min-height:110px; }
QLabel#StripTitle { color:#7792AB; font-size:8px; font-weight:850; letter-spacing:.8px; background:transparent; }
QLabel#LastTakeIcon { background:#0B1B2A; border:1px solid #203D57; border-radius:6px; }
QLabel#LastTakeName { color:#F4F8FC; font-size:11px; font-weight:750; background:transparent; }
QLabel#LastTakeMeta { color:#8CA2B8; font-family:"SF Mono",Consolas,monospace; font-size:8px; background:transparent; }
QLabel#LastTakeNote { color:#8DA4B8; font-size:9px; font-style:italic; background:transparent; }
QPushButton#MiniPlayButton { background:#0A1C2D; border:1px solid #345878; border-radius:20px; padding:0; }
QPushButton#MiniPlayButton:hover { background:#12304B; }
QLabel#HistoryRow { color:#C4D2DF; background:#081522; border-bottom:1px solid #132A3E; padding:2px 7px; font-family:"SF Mono",Consolas,monospace; font-size:8px; }
QTextEdit#QuickNotes { background:#07131F; border:1px solid #223C54; border-radius:6px; font-size:9px; padding:6px; }
QFrame#StripDivider { color:#1A3349; background:#1A3349; border:0; max-width:1px; }
QLabel#FooterMessage { color:#8095A8; font-size:8px; background:transparent; margin-left:8px; }

/* Take review / waveform */
QFrame#TakeInspector {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0B1A28, stop:1 #07131F);
    border:1px solid #1A344C; border-radius:10px; min-width:390px;
}
QLabel#TakeInspectorTitle { color:#F4F8FC; font-size:14px; font-weight:850; letter-spacing:.4px; background:transparent; }
QLabel#TakeInspectorMeta { color:#829CB4; font-family:"SF Mono",Consolas,monospace; font-size:9px; background:transparent; }
QWidget#WaveformWidget { background:#06111B; border:0; }
QLabel#TakePlaybackTime { color:#AFC4D7; font-family:"SF Mono",Consolas,monospace; font-size:10px; background:transparent; }
QTextEdit#SelectedTakeNotes { background:#07131F; border:1px solid #28445D; border-radius:7px; font-size:10px; padding:7px; }

/* ISO routing / post-converter trim */
QFrame#RoutingPanel { background:#081522; border:1px solid #1A344C; border-radius:9px; }
QScrollArea#RoutingScroll { background:transparent; border:0; }
QLabel#RoutingTrackLabel { color:#DDE8F2; font-size:10px; font-weight:750; background:transparent; }
QComboBox#RouteSourceCombo { min-height:25px; padding:4px 26px 4px 8px; font-size:9px; }
QLabel#TrimValue { color:#9EC2DE; font-family:"SF Mono",Consolas,monospace; font-size:9px; background:transparent; }
QSlider#RecordTrimSlider::groove:horizontal { height:5px; background:#102A3E; border-radius:2px; }
QSlider#RecordTrimSlider::sub-page:horizontal { background:#1C86D1; border-radius:2px; }
QSlider#RecordTrimSlider::handle:horizontal { width:14px; margin:-5px 0; border-radius:7px; background:#D9EEFF; border:1px solid #3A7EAF; }
QSlider#RecordTrimSlider::handle:horizontal:hover { background:#FFFFFF; border-color:#52AFFF; }

/* Tables / secondary pages */
QTableWidget#TakeTable { background:#081522; alternate-background-color:#0A1927; border:1px solid #1D3950; border-radius:8px; gridline-color:transparent; selection-background-color:#123F64; selection-color:#FFFFFF; }
QHeaderView::section { background:#0B1A28; color:#7994AE; border:0; border-bottom:1px solid #254159; padding:8px; font-size:9px; font-weight:800; }
QTableWidget::item { border-bottom:1px solid #142B3E; padding:7px; }
QLabel#DiagnosticValue { color:#C8D9E8; font-family:"SF Mono",Consolas,monospace; background:transparent; }

/* Footer */
QFrame#FooterBar { background:transparent; border-top:1px solid #10263A; }
QLabel#FooterReady { color:#4BE696; font-size:9px; background:transparent; }
QLabel#FooterText { color:#71879B; font-size:8px; background:transparent; margin-left:12px; }

QCheckBox { color:#B4C5D5; spacing:7px; }
QCheckBox::indicator { width:15px; height:15px; background:#07131F; border:1px solid #31506A; border-radius:3px; }
QCheckBox::indicator:checked { background:#1678D2; border-color:#2496FF; }
QScrollBar:vertical { background:#06111B; width:8px; }
QScrollBar::handle:vertical { background:#27445D; min-height:28px; border-radius:4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
"""
