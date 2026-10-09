#define AppVersion "1.2.0"
[Setup]
AppId=io.aural.Aural
AppName=Aural
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Aural
DefaultGroupName=Aural
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\..\dist
OutputBaseFilename=Aural-Windows-x64-Installer
SetupIconFile=..\..\static\aural.ico
UninstallDisplayIcon={app}\Aural.exe
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\..\dist\Aural\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\static\aural.ico"; DestDir: "{localappdata}\Aural\icons"; Flags: onlyifdoesntexist uninsneveruninstall
[Icons]
Name: "{group}\Aural"; Filename: "{app}\Aural.exe"; WorkingDir: "{app}"; IconFilename: "{localappdata}\Aural\icons\aural.ico"
Name: "{autodesktop}\Aural"; Filename: "{app}\Aural.exe"; WorkingDir: "{app}"; IconFilename: "{localappdata}\Aural\icons\aural.ico"; Tasks: desktopicon
[Run]
Filename: "{app}\Aural.exe"; Description: "Launch Aural"; Flags: nowait postinstall skipifsilent
