"""GM-AI-Hub 시스템 트레이 런처.

pystray 기반 시스템 트레이 아이콘.
FastAPI 서버를 서브프로세스로 시작하고 브라우저를 연다.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

# ── 설정 ──────────────────────────────────────────────────────────────
_HOST = "127.0.0.1"
_PORT = 8080
_URL = f"http://{_HOST}:{_PORT}"
_HEALTH_URL = f"{_URL}/api/health"
_MAX_WAIT = 30  # 서버 시작 대기 최대 초


def _find_icon() -> Path | None:
    """아이콘 파일 위치 탐색."""
    candidates = [
        Path(__file__).parent / "icon.ico",
        Path(__file__).parent / "icon.png",
    ]
    # PyInstaller 번들인 경우
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        candidates = [
            base / "launcher" / "icon.ico",
            base / "launcher" / "icon.png",
        ] + candidates
    for p in candidates:
        if p.exists():
            return p
    return None


def _create_default_icon() -> Image.Image:
    """아이콘 파일이 없을 때 기본 아이콘 생성."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 초록 배경 원
    draw.ellipse([2, 2, size - 2, size - 2], fill=(0, 122, 94, 255))
    # 흰색 "G" 텍스트
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "G", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), "G", fill="white", font=font)
    return img


def _load_icon() -> Image.Image:
    """아이콘 로드 또는 기본 생성."""
    icon_path = _find_icon()
    if icon_path:
        try:
            return Image.open(icon_path)
        except Exception:
            pass
    return _create_default_icon()


_MAX_RESTARTS = 5          # 연속 재시작 최대 횟수
_HEALTH_INTERVAL = 5       # 헬스 체크 주기 (초)
_HEALTH_FAIL_THRESHOLD = 3 # 연속 실패 N회 시 재시작


def _log_dir() -> Path:
    """서버 로그 디렉토리."""
    local = os.environ.get("LOCALAPPDATA")
    if local:
        d = Path(local) / "GM-AI-Hub" / "logs"
    else:
        d = Path.home() / ".gm-ai-hub" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


class TrayApp:
    """시스템 트레이 애플리케이션."""

    def __init__(self):
        self._server_proc: subprocess.Popen | None = None
        self._running = False
        self._icon = None
        self._log_file = None

    def _get_server_command(self) -> list[str]:
        """서버 실행 명령어 결정."""
        if getattr(sys, "frozen", False):
            # PyInstaller 번들: 같은 디렉토리의 gm-hub-server.exe
            base = Path(sys.executable).parent
            server_exe = base / "gm-hub-server.exe"
            if server_exe.exists():
                return [str(server_exe)]
            # fallback: 같은 exe에 --server 플래그
            return [sys.executable, "--server"]
        else:
            # 개발 모드: python -m backend.main
            return [sys.executable, "-m", "backend.main"]

    def start_server(self) -> bool:
        """FastAPI 서버 시작."""
        if self._server_proc and self._server_proc.poll() is None:
            return True  # 이미 실행 중

        cmd = self._get_server_command()
        try:
            # 서버 프로세스 시작 (콘솔 숨김)
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            # stderr를 로그 파일로 저장 (서버 크래시 진단용)
            log_path = _log_dir() / "server.log"
            self._log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115

            self._server_proc = subprocess.Popen(
                cmd,
                stdout=self._log_file,
                stderr=self._log_file,
                creationflags=creation_flags,
            )
            self._running = True
            return True
        except Exception as e:
            try:
                log_path = _log_dir() / "server.log"
                log_path.write_text(f"서버 시작 실패: {e}\n", encoding="utf-8")
            except Exception:
                pass
            return False

    def wait_for_server(self) -> bool:
        """서버 health 엔드포인트 대기."""
        for _ in range(_MAX_WAIT):
            try:
                r = httpx.get(_HEALTH_URL, timeout=2)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def stop_server(self):
        """서버 프로세스 종료."""
        self._running = False
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()
            try:
                self._server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_proc.kill()
        self._server_proc = None
        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None

    def open_browser(self):
        """기본 브라우저에서 앱 열기."""
        webbrowser.open(_URL)

    def _monitor_server(self):
        """서버 감시: 프로세스 종료 또는 응답 없음 시 자동 재시작.

        - 절전 복귀 후 서버가 죽거나 응답 불능 → 자동 재시작 (최대 N회)
        - 사용자가 /api/quit으로 정상 종료 (exit code 0) → 트레이도 종료
        """
        restart_count = 0
        health_fail = 0

        while self._running:
            time.sleep(_HEALTH_INTERVAL)
            if not self._running:
                return

            # ── 1. 프로세스 종료 감지 ──
            if self._server_proc and self._server_proc.poll() is not None:
                exit_code = self._server_proc.returncode
                self._server_proc = None

                # 정상 종료 (사용자 /api/quit) → 트레이도 종료
                if exit_code == 0:
                    self._running = False
                    if self._icon:
                        self._icon.stop()
                    return

                # 비정상 종료 → 재시작
                if restart_count >= _MAX_RESTARTS:
                    self._running = False
                    if self._icon:
                        self._icon.stop()
                    return

                restart_count += 1
                time.sleep(2)
                if self.start_server() and self.wait_for_server():
                    health_fail = 0
                    continue
                # 재시작 실패 → 종료
                self._running = False
                if self._icon:
                    self._icon.stop()
                return

            # ── 2. 헬스 체크 (프로세스 alive but 응답 없음 — 절전 복귀) ──
            try:
                r = httpx.get(_HEALTH_URL, timeout=3)
                if r.status_code == 200:
                    health_fail = 0
                    restart_count = 0  # 안정 → 카운터 리셋
                    continue
            except Exception:
                pass

            health_fail += 1
            if health_fail >= _HEALTH_FAIL_THRESHOLD:
                if restart_count >= _MAX_RESTARTS:
                    self._running = False
                    if self._icon:
                        self._icon.stop()
                    return

                restart_count += 1
                health_fail = 0
                self.stop_server()
                time.sleep(2)
                if self.start_server() and self.wait_for_server():
                    continue
                self._running = False
                if self._icon:
                    self._icon.stop()
                return

    def _monitor_server_port(self):
        """헬스 체크 기반 서버 감시 (프로세스를 소유하지 않는 경우).

        이전 세션에서 서버가 남아 있을 때 트레이가 이를 인계받은 뒤 사용.
        서버가 응답하지 않으면 자체 서버를 시작한다.
        """
        health_fail = 0
        while self._running:
            time.sleep(_HEALTH_INTERVAL)
            if not self._running:
                return
            try:
                r = httpx.get(_HEALTH_URL, timeout=3)
                if r.status_code == 200:
                    health_fail = 0
                    continue
            except Exception:
                pass

            health_fail += 1
            if health_fail >= _HEALTH_FAIL_THRESHOLD:
                # 인계 서버 응답 없음 → 자체 서버 시작 후 프로세스 모니터로 전환
                if self.start_server() and self.wait_for_server():
                    self._monitor_server()
                else:
                    self._running = False
                    if self._icon:
                        self._icon.stop()
                return

    def restart_server(self):
        """서버 재시작."""
        self.stop_server()
        time.sleep(1)
        if self.start_server():
            self.wait_for_server()

    def run(self):
        """트레이 앱 실행."""
        import pystray

        icon_image = _load_icon()

        def on_open(icon, item):
            self.open_browser()

        def on_restart(icon, item):
            threading.Thread(target=self.restart_server, daemon=True).start()

        def on_stop(icon, item):
            self.stop_server()

        def on_quit(icon, item):
            self.stop_server()
            icon.stop()

        menu = pystray.Menu(
            pystray.MenuItem("GM-AI-Hub 열기", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("서버 재시작", on_restart),
            pystray.MenuItem("서버 중지", on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", on_quit),
        )

        icon = pystray.Icon("GM-AI-Hub", icon_image, "GM-AI-Hub", menu)
        self._icon = icon

        # 서버 시작 + 브라우저 열기를 백그라운드에서 실행
        def startup():
            # 이전 세션에서 서버가 이미 실행 중인지 확인 (고아 서버 인계)
            server_adopted = False
            try:
                r = httpx.get(_HEALTH_URL, timeout=1.5)
                if r.status_code == 200:
                    server_adopted = True
            except Exception:
                pass

            if server_adopted:
                self._running = True
                self.open_browser()
                threading.Thread(target=self._monitor_server_port, daemon=True).start()
                return

            if self.start_server():
                if self.wait_for_server():
                    self.open_browser()
                    # 서버 종료 감시 (브라우저 UI의 종료 버튼 대응)
                    threading.Thread(target=self._monitor_server, daemon=True).start()
                else:
                    # 서버 프로세스 상태 로그
                    rc = self._server_proc.poll() if self._server_proc else "N/A"
                    msg = f"서버 시작 대기 시간 초과 (exit code: {rc})"
                    try:
                        log_path = _log_dir() / "server.log"
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(f"\n{msg}\n")
                    except Exception:
                        pass
            else:
                try:
                    log_path = _log_dir() / "server.log"
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write("서버 프로세스 시작 실패\n")
                except Exception:
                    pass

        threading.Thread(target=startup, daemon=True).start()
        icon.run()


_MUTEX_NAME = "Global\\GM-AI-Hub-Tray-SingleInstance"


def main():
    """엔트리 포인트.

    Windows 명명 뮤텍스로 트레이 단일 인스턴스를 보장한다.
    - 트레이가 이미 살아 있으면 → 브라우저만 열고 종료
    - 트레이가 없고 서버만 남아 있으면 → 트레이를 새로 띄우고 서버를 인계
    - 둘 다 없으면 → 트레이 + 서버 정상 시작
    """
    # 뮤텍스 취득 시도 (Windows 전용)
    _mutex_handle = None
    if sys.platform == "win32":
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            # 다른 트레이 인스턴스가 실행 중 → 브라우저만 열고 종료
            webbrowser.open(_URL)
            return

    # 뮤텍스를 취득했으므로 이 프로세스가 트레이를 담당
    # startup() 내부에서 고아 서버를 자동으로 감지하고 인계한다
    app = TrayApp()
    app.run()

    # 트레이 종료 시 뮤텍스 해제
    if _mutex_handle and sys.platform == "win32":
        ctypes.windll.kernel32.ReleaseMutex(_mutex_handle)
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)


if __name__ == "__main__":
    main()
