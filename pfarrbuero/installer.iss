#define MyAppName "COMPELEC ONE Pfarrbuero-KI"
#define MyAppVersion "1.3.0"
[Setup]
AppId={{BFA87B7C-1F39-4B41-AB71-91F4A9A81013}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\COMPELEC ONE\Pfarrbuero-KI
DefaultGroupName=COMPELEC ONE
OutputDir=dist
OutputBaseFilename=COMPELEC_ONE_Pfarrbuero_KI_V1.3_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "dist\COMPELEC_ONE_Pfarrbuero_KI.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\COMPELEC ONE Pfarrbuero-KI"; Filename: "{app}\COMPELEC_ONE_Pfarrbuero_KI.exe"
Name: "{autodesktop}\COMPELEC ONE Pfarrbuero-KI"; Filename: "{app}\COMPELEC_ONE_Pfarrbuero_KI.exe"
[Run]
Filename: "{app}\COMPELEC_ONE_Pfarrbuero_KI.exe"; Description: "Pfarrbuero-KI starten"; Flags: nowait postinstall skipifsilent
