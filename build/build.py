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
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SPEC_FILE = PROJECT_ROOT / "build" / "gm-ai-hub.spec"
ISS_FILE = PROJECT_ROOT / "installer" / "gm-ai-hub.iss"


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


def step_pyinstaller():
    """3. PyInstaller 동결."""
    print("\n[3/4] PyInstaller 빌드")
    if not SPEC_FILE.exists():
        print(f"  spec 파일 없음: {SPEC_FILE}")
        sys.exit(1)

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
    """4. Inno Setup 인스톨러 생성."""
    print("\n[4/4] Inno Setup 인스톨러")
    if not ISS_FILE.exists():
        print(f"  iss 파일 없음: {ISS_FILE}")
        sys.exit(1)

    # ISCC 경로 탐색
    iscc_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    iscc = None
    for p in iscc_paths:
        if p.exists():
            iscc = str(p)
            break

    if not iscc:
        # PATH에서 찾기
        iscc = shutil.which("ISCC")

    if not iscc:
        print("  Inno Setup (ISCC.exe) 를 찾을 수 없습니다.")
        print("  https://jrsoftware.org/isinfo.php 에서 설치하세요.")
        print("  인스톨러 생성을 건너뜁니다.")
        return

    run([iscc, str(ISS_FILE)], cwd=PROJECT_ROOT / "installer", shell=True)
    print("  인스톨러 생성 완료!")


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
