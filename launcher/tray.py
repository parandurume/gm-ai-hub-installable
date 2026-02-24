"""GM-AI-Hub 시스템 트레이 런처.

pystray 기반 시스템 트레이 아이콘.
FastAPI 서버를 서브프로세스로 시작하고 브라우저를 연다.
"""

from __future__ import annotations

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


class TrayApp:
    """시스템 트레이 애플리케이션."""

    def __init__(self):
        self._server_proc: subprocess.Popen | None = None
        self._running = False

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

            self._server_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
            )
            self._running = True
            return True
        except Exception as e:
            print(f"서버 시작 실패: {e}")
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

    def open_browser(self):
        """기본 브라우저에서 앱 열기."""
        webbrowser.open(_URL)

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

        # 서버 시작 + 브라우저 열기를 백그라운드에서 실행
        def startup():
            if self.start_server():
                if self.wait_for_server():
                    self.open_browser()
                else:
                    print("서버 시작 대기 시간 초과")
            else:
                print("서버 시작 실패")

        threading.Thread(target=startup, daemon=True).start()
        icon.run()


def main():
    """엔트리 포인트."""
    app = TrayApp()
    app.run()


if __name__ == "__main__":
    main()
