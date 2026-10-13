#define MyAppName "Achievement Manager"
#define MyAppVersion "0.7.0-beta.2"
#define MyAppPublisher "Achievement Manager Contributors"
#define MyAppExeName "AchievementManager.exe"
[Setup]
AppId={{D9C29A73-4777-4A0D-B823-1D62D3D08F46}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AchievementManager
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=AchievementManager-Setup-v0.7.0-beta.2
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
[Files]
Source: "..\dist\AchievementManager\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{group}\Achievement Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Achievement Manager"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加のショートカット:"; Flags: unchecked
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Achievement Managerを起動"; Flags: nowait postinstall skipifsilent
