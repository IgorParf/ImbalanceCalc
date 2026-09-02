; Інсталятор ImbalanceCalc для Windows (Inno Setup 6).
;
; Збирати після installer/build.ps1:
;     iscc installer\setup.iss
;
; Встановлення відбувається в %LOCALAPPDATA%\Programs — без прав
; адміністратора, тому ані встановлення, ані оновлення не викликають UAC.

#define AppName "ImbalanceCalc"
; Версію передає build.ps1 (/DAppVersion=...), беручи її з imbalance_calc.__version__.
#ifndef AppVersion
  #define AppVersion "0.1.1"
#endif
#define AppPublisher "IgorParf"
#define AppExeName "ImbalanceCalc.exe"
#define AppURL "https://github.com/IgorParf/ImbalanceCalc"

[Setup]
AppId={{9E2C1B74-5F3A-4D8E-B1C6-7A0E5D2F4831}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName=Небаланси електричної енергії
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=ImbalanceCalc-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=app.ico

[Languages]
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Небаланси електричної енергії"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Небаланси електричної енергії"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Логи створюються під час роботи, тому інсталятор про них не знає.
; Сховище періодів (data/store) свідомо НЕ видаляємо — це дані користувача.
Type: filesandordirs; Name: "{localappdata}\{#AppName}\logs"
