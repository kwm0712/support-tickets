#define MyAppName "COMPELEC ONE Business"
#define MyAppVersion "0.3.0-dev"
#define MyAppPublisher "Compelec Computersysteme GmbH"
#define MyAppExeName "COMPELEC-ONE-Business.exe"

[Setup]
AppId={{B95D43C9-0D0A-48F9-A7B9-CCE0A30E0C03}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\COMPELEC\ONE Business
DefaultGroupName=COMPELEC ONE
DisableProgramGroupPage=yes
OutputDir=..\..\release\windows
OutputBaseFilename=COMPELEC-ONE-Business-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayName={#MyAppName}
VersionInfoVersion=0.3.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=COMPELEC ONE Business - AI Support & Knowledge
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Files]
Source: "..\..\dist\COMPELEC-ONE-Business\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion
Source: "..\..\docs\BACKUP_RESTORE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\COMPELEC ONE Business"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\COMPELEC ONE Business"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Verknüpfungen:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "COMPELEC ONE Business starten"; Flags: nowait postinstall skipifsilent
