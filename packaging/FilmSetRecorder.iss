#define MyAppName "FilmSet Recorder"
#define MyAppVersion "0.6.4"
#define MyAppExeName "FilmSetRecorder.exe"

[Setup]
AppId={{B560CBAA-ED80-42D5-B7CB-341CA73871C4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={localappdata}\Programs\FilmSet Recorder
DefaultGroupName=FilmSet Recorder
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=FilmSetRecorder_Setup_0.6.4
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\assets\icon.ico
SetupLogging=yes
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\FilmSetRecorder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\icon.ico"; DestDir: "{app}"; DestName: "FilmSetRecorder.ico"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\FilmSet Recorder"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\FilmSetRecorder.ico"
Name: "{autodesktop}\FilmSet Recorder"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\FilmSetRecorder.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch FilmSet Recorder"; Flags: nowait postinstall skipifsilent
