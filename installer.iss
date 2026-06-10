; Inno Setup script для «Видео-компрессор»
; Сборка: "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
; Результат: installer\VideoCompressor-Setup.exe — один файл для раздачи.

#define AppName "Видео-компрессор"
#define AppVersion "1.0.0"
#define AppPublisher "no harm org"
#define AppCopyright "(c) 2026 Kirkamah / no harm org"
#define AppExeName "VideoCompressor.exe"

[Setup]
AppId={{8B2E6C41-9F3A-4D7E-B1C2-7A5E0D9F4C10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright={#AppCopyright}
; Установка без прав администратора, в профиль пользователя.
PrivilegesRequired=lowest
DefaultDirName={autopf}\VideoCompressor
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=VideoCompressor-Setup
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "contextmenu"; Description: "Добавить пункт «Сжать видео» в контекстное меню (правый клик по видео)"; GroupDescription: "Интеграция с Проводником:"

[Files]
Source: "dist\VideoCompressor\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Регистрируем пункт меню (с обновлением Проводника), если выбрана задача.
Filename: "{app}\{#AppExeName}"; Parameters: "--install-menu --refresh"; Tasks: contextmenu; Flags: runhidden; StatusMsg: "Регистрация пункта «Сжать видео»..."
; Предложить запуск после установки.
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Убираем пункт меню при удалении (до удаления файлов).
Filename: "{app}\{#AppExeName}"; Parameters: "--uninstall-menu"; Flags: runhidden; RunOnceId: "RemoveContextMenu"
