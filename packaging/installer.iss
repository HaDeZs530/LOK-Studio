; Inno Setup script — builds LOK-Studio-Setup.exe from the PyInstaller onedir output.
; CI runs:  iscc /DAppVersion=0.2.1 packaging\installer.iss
; Local:    build with the spec first, then run this from the repo root.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8F3C1A64-6E2B-4E9F-9C1D-2A7B5E4D9C03}
AppName=LOK Studio
AppVersion={#AppVersion}
AppPublisher=HaDeZs
AppPublisherURL=https://github.com/HaDeZs530/LOK-Studio
DefaultDirName={autopf}\LOK Studio
DefaultGroupName=LOK Studio
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=LOK-Studio-Setup
SetupIconFile=lok.ico
UninstallDisplayIcon={app}\LOK-Studio.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
; the whole onedir build — exe plus its _internal folder
Source: "..\dist\LOK-Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LOK Studio"; Filename: "{app}\LOK-Studio.exe"
Name: "{autodesktop}\LOK Studio"; Filename: "{app}\LOK-Studio.exe"; Tasks: desktopicon

[Run]
; no skipifsilent — a silent run is the in-app updater, and it must come back up
Filename: "{app}\LOK-Studio.exe"; Description: "Launch LOK Studio"; Flags: nowait postinstall
