#define MyAppName "DictaType"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DictaType contributors"
#define MyAppExeName "DictaType.exe"

; French neural voice compatibility layer.
; Newer workflows may stage assets\voices\french.onnx, while older workflows
; keep Piper's original fr_FR-siwis-medium filenames. Accept either source and
; always install the stable runtime names expected by DictaType.
#define FrenchModelSimple "assets\voices\french.onnx"
#define FrenchConfigSimple "assets\voices\french.onnx.json"
#define FrenchModelPiper "assets\voices\fr_FR-siwis-medium.onnx"
#define FrenchConfigPiper "assets\voices\fr_FR-siwis-medium.onnx.json"

#if FileExists(FrenchModelSimple)
  #define FrenchModelSource FrenchModelSimple
#elif FileExists(FrenchModelPiper)
  #define FrenchModelSource FrenchModelPiper
#else
  #error French neural model is missing. Expected assets\voices\french.onnx or assets\voices\fr_FR-siwis-medium.onnx
#endif

#if FileExists(FrenchConfigSimple)
  #define FrenchConfigSource FrenchConfigSimple
#elif FileExists(FrenchConfigPiper)
  #define FrenchConfigSource FrenchConfigPiper
#else
  #error French neural configuration is missing. Expected assets\voices\french.onnx.json or assets\voices\fr_FR-siwis-medium.onnx.json
#endif

[Setup]
AppId={{47B47A92-10DA-4E45-81EB-9C5F746021A9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DictaType
DefaultGroupName=DictaType
DisableProgramGroupPage=yes
OutputDir=installer-output
OutputBaseFilename=DictaType-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
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
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#FrenchModelSource}"; DestDir: "{app}\voices"; DestName: "french.onnx"; Flags: ignoreversion
Source: "{#FrenchConfigSource}"; DestDir: "{app}\voices"; DestName: "french.onnx.json"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch DictaType"; Flags: nowait postinstall skipifsilent
