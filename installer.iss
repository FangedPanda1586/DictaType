#define MyAppName "DictaType"
#define MyAppVersion "1.0.0-rc.1"
#define MyAppPublisher "DictaType contributors"
#define MyAppExeName "DictaType.exe"

[Setup]
AppId={{47B47A92-10DA-4E45-81EB-9C5F746021A9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf}\DictaType
DefaultGroupName=DictaType
DisableProgramGroupPage=yes
OutputDir=installer-output
OutputBaseFilename=DictaType-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=LICENSE
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=dictatype.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; The complete PyInstaller one-folder bundle is installed intact. This keeps
; Piper, eSpeak and ONNX native files in the exact layout tested by CI.
Source: "dist\DictaType\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch DictaType"; Flags: nowait postinstall skipifsilent
