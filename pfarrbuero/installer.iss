#define MyAppName "COMPELEC ONE Pfarrbüro-KI"
#define MyAppVersion "2.0.0-dev"
[Setup]
AppId={{BFA87B7C-1F39-4B41-AB71-91F4A9A81013}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\COMPELEC ONE\Pfarrbüro-KI
DefaultGroupName=COMPELEC ONE
OutputDir=..\dist
OutputBaseFilename=COMPELEC_ONE_Pfarrbuero_KI_V2.0_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "..\dist\COMPELEC_ONE_Pfarrbuero_KI.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\COMPELEC ONE Pfarrbüro-KI"; Filename: "{app}\COMPELEC_ONE_Pfarrbuero_KI.exe"
Name: "{autodesktop}\COMPELEC ONE Pfarrbüro-KI"; Filename: "{app}\COMPELEC_ONE_Pfarrbuero_KI.exe"
[Run]
Filename: "{app}\COMPELEC_ONE_Pfarrbuero_KI.exe"; Description: "Pfarrbüro-KI starten"; Flags: nowait postinstall skipifsilent
