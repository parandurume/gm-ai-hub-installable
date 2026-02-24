"""GM-AI-Hub 빌드 스크립트.

사용법:
  python build/build.py             # 전체 빌드
  python build/build.py --skip-tests   # 테스트 건너뛰기
  python build/build.py --skip-installer  # 인스톨러 건너뛰기
  python build/build.py --frontend-only   # 프론트엔드만 빌드

빌드 순서:
  1. npm install + npm run build (frontend → frontend/dist/)
  2. pytest tests/ -v (전체 테스트)
  3. pyinstaller build/gm-ai-hub.spec --clean (동결)
  4. ISCC installer/gm-ai-hub.iss (인스톨러 생성)
     - Inno Setup이 없으면 winget으로 자동 설치 후 진행
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SPEC_FILE = PROJECT_ROOT / "build" / "gm-ai-hub.spec"
ISS_FILE = PROJECT_ROOT / "installer" / "gm-ai-hub.iss"

_ISCC_CANDIDATES = [
    # system-wide (admin install)
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    # per-user (winget default, no admin required)
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
]


def run(
    cmd: list[str], cwd: Path | None = None, check: bool = True, shell: bool = False,
) -> int:
    """명령 실행 및 결과 출력."""
    print(f"\n{'='*60}")
    print(f"  실행: {' '.join(cmd)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell)
    if check and result.returncode != 0:
        print(f"\n  실패! (exit code {result.returncode})")
        sys.exit(result.returncode)
    return result.returncode


def _find_iscc() -> str | None:
    """설치된 ISCC.exe 경로를 반환. 없으면 None."""
    for p in _ISCC_CANDIDATES:
        if p.exists():
            return str(p)

    found = shutil.which("ISCC")
    if found:
        return found

    # 레지스트리에서 설치 경로 탐색 (winget/수동 설치 위치 무관하게 동작)
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for base in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ):
                try:
                    key = winreg.OpenKey(hive, base)
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, sub)
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                if "Inno Setup" in str(name):
                                    loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    iscc = Path(loc) / "ISCC.exe"
                                    if iscc.exists():
                                        return str(iscc)
                            except FileNotFoundError:
                                pass
                            i += 1
                        except OSError:
                            break
                except OSError:
                    continue
    except ImportError:
        pass

    return None


def _install_inno_setup() -> None:
    """winget으로 Inno Setup 6을 자동 설치한다."""
    print("  Inno Setup을 찾을 수 없습니다. winget으로 자동 설치합니다...")
    winget = shutil.which("winget")
    if not winget:
        print("  winget을 찾을 수 없습니다.")
        print("  Inno Setup을 수동 설치하세요: https://jrsoftware.org/isinfo.php")
        sys.exit(1)

    result = subprocess.run(
        [
            winget, "install",
            "--id", "JRSoftware.InnoSetup",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
    )
    if result.returncode != 0:
        print("  winget 설치 실패. 수동으로 설치하세요: https://jrsoftware.org/isinfo.php")
        sys.exit(1)
    print("  Inno Setup 설치 완료.")


def step_frontend():
    """1. 프론트엔드 빌드."""
    print("\n[1/4] 프론트엔드 빌드")
    if not (FRONTEND_DIR / "package.json").exists():
        print("  frontend/package.json 없음 — 건너뜀")
        return

    # Windows에서 npm/npx는 .cmd 파일이므로 shell=True 필요
    run(["npm", "install"], cwd=FRONTEND_DIR, shell=True)
    run(["npx", "vite", "build"], cwd=FRONTEND_DIR, shell=True)

    dist = FRONTEND_DIR / "dist"
    if not (dist / "index.html").exists():
        print("  프론트엔드 빌드 결과 확인 실패!")
        sys.exit(1)
    print(f"  빌드 완료: {dist}")


def step_tests():
    """2. 테스트 실행."""
    print("\n[2/4] 테스트 실행")
    run([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=PROJECT_ROOT)


def _kill_running_app() -> None:
    """빌드 전 실행 중인 GM-AI-Hub 프로세스를 종료한다.

    dist/ 폴더는 shutil.rmtree로 삭제되는데, Windows는 실행 중인 EXE를
    잠그기 때문에 앱이 켜진 상태에서 빌드하면 PermissionError가 발생한다.
    """
    targets = {"GM-AI-Hub.exe", "gm-hub-server.exe"}
    killed = []
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        for line in result.stdout.splitlines():
            # CSV 형식: "프로세스명","PID",...
            parts = line.strip().strip('"').split('","')
            if parts and parts[0] in targets:
                pid = parts[1] if len(parts) > 1 else ""
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                killed.append(parts[0])
    except Exception:
        pass

    if killed:
        print(f"  실행 중인 앱 종료: {', '.join(killed)}")
        import time
        time.sleep(1)  # 프로세스 종료 대기


def step_pyinstaller():
    """3. PyInstaller 동결."""
    print("\n[3/4] PyInstaller 빌드")
    if not SPEC_FILE.exists():
        print(f"  spec 파일 없음: {SPEC_FILE}")
        sys.exit(1)

    # 실행 중인 앱 종료 (Windows EXE 잠금 방지)
    _kill_running_app()

    # 이전 빌드 정리
    dist_dir = PROJECT_ROOT / "dist"
    build_tmp = PROJECT_ROOT / "build_tmp"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_tmp.exists():
        shutil.rmtree(build_tmp)

    run([
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--distpath", str(dist_dir),
        "--workpath", str(build_tmp),
    ], cwd=PROJECT_ROOT)

    output = dist_dir / "GM-AI-Hub"
    if not (output / "GM-AI-Hub.exe").exists():
        print("  PyInstaller 빌드 결과 확인 실패!")
        sys.exit(1)
    print(f"  빌드 완료: {output}")

    # 빌드 캐시 정리
    if build_tmp.exists():
        shutil.rmtree(build_tmp)


def step_installer():
    """4. Inno Setup 인스톨러 생성.

    ISCC.exe가 없으면 winget으로 자동 설치하고 진행한다.
    설치 후 PATH에 반영되지 않을 수 있으므로 고정 경로를 다시 확인한다.
    """
    print("\n[4/4] Inno Setup 인스톨러")
    if not ISS_FILE.exists():
        print(f"  iss 파일 없음: {ISS_FILE}")
        sys.exit(1)

    iscc = _find_iscc()
    if not iscc:
        _install_inno_setup()
        # winget 설치 후 PATH 갱신 없이 고정 경로 재탐색
        iscc = _find_iscc()

    if not iscc:
        print("  Inno Setup 설치 후에도 ISCC.exe를 찾을 수 없습니다.")
        print("  터미널을 재시작한 뒤 다시 시도하거나, 직접 실행하세요:")
        print(f'    ISCC "{ISS_FILE}"')
        sys.exit(1)

    run([iscc, str(ISS_FILE)], cwd=PROJECT_ROOT / "installer", shell=True)

    output_dir = PROJECT_ROOT / "installer" / "Output"
    installers = list(output_dir.glob("*.exe")) if output_dir.exists() else []
    if not installers:
        print("  인스톨러 파일을 찾을 수 없습니다!")
        sys.exit(1)
    print(f"  인스톨러 생성 완료: {installers[0]}")


def main():
    parser = argparse.ArgumentParser(description="GM-AI-Hub 빌드 스크립트")
    parser.add_argument("--skip-tests", action="store_true", help="테스트 건너뛰기")
    parser.add_argument("--skip-installer", action="store_true", help="인스톨러 건너뛰기")
    parser.add_argument("--frontend-only", action="store_true", help="프론트엔드만 빌드")
    args = parser.parse_args()

    print("GM-AI-Hub Desktop 빌드")
    print(f"  프로젝트: {PROJECT_ROOT}")

    step_frontend()

    if args.frontend_only:
        print("\n프론트엔드 빌드 완료!")
        return

    if not args.skip_tests:
        step_tests()

    step_pyinstaller()

    if not args.skip_installer:
        step_installer()

    print(f"\n{'='*60}")
    print("  빌드 완료!")
    print(f"  실행 파일: {PROJECT_ROOT / 'dist' / 'GM-AI-Hub' / 'GM-AI-Hub.exe'}")
    installer_dir = PROJECT_ROOT / "installer" / "Output"
    if installer_dir.exists():
        installers = list(installer_dir.glob("*.exe"))
        if installers:
            print(f"  인스톨러:  {installers[0]}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
