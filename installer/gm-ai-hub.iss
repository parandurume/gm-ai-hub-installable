; GM-AI-Hub Desktop Installer — Inno Setup Script
; 실행: ISCC installer\gm-ai-hub.iss

#define MyAppName "GM-AI-Hub"
#define MyAppVersion "2.0.1"
#define MyAppPublisher "GM-AI-Hub Project"
#define MyAppURL "http://127.0.0.1:8080"
#define MyAppExeName "GM-AI-Hub.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=license_ko.txt
OutputDir=Output
OutputBaseFilename=GM-AI-Hub-Setup-{#MyAppVersion}
SetupIconFile=..\launcher\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
; 한국어 기본
ShowLanguageDialog=no

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 아이콘:"; Flags: unchecked
Name: "downloadstt"; Description: "음성 인식(STT) 모델 다운로드 — 약 1.5 GB, 인터넷 연결 필요"; GroupDescription: "기능 설치 (선택):"; Flags: unchecked

[Files]
; PyInstaller 출력 폴더 전체 복사
Source: "..\dist\GM-AI-Hub\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; STT 모델 다운로드 (선택 작업 체크 시에만 실행)
Filename: "{app}\gm-hub-server.exe"; Parameters: "--download-stt"; Description: "음성 인식 모델 다운로드 중..."; Flags: waituntilterminated; Tasks: downloadstt
; 설치 후 앱 실행 옵션
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} 실행"; Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
; 로그, 캐시 등 제거 (사용자 데이터는 보존)
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\*.log"

[Code]
// Ollama 설치 여부 확인 후 안내
procedure CurStepChanged(CurStep: TSetupStep);
var
  OllamaPath: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    OllamaPath := ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe');
    if not FileExists(OllamaPath) then
    begin
      if MsgBox(
        'Ollama AI 엔진이 설치되어 있지 않습니다.' + #13#10 +
        'GM-AI-Hub의 AI 기능을 사용하려면 Ollama가 필요합니다.' + #13#10#13#10 +
        'Ollama 다운로드 페이지를 열겠습니까?',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        ShellExec('open', 'https://ollama.com/download', '', '', SW_SHOW, ewNoWait, ResultCode);
      end;
    end;
  end;
end;
