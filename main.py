"""카카오톡 오픈채팅 Instagram 수집기."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KakaoTalk open chat Instagram collector")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path.cwd(),
        help="설정/데이터 기준 디렉터리",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Tkinter GUI 모드",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="콘솔 백그라운드 모드",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir = args.base_dir.resolve()

    if sys.platform != "win32":
        print("경고: UI Automation은 Windows에서만 동작합니다. parser/DB 테스트는 가능합니다.")

    from config.settings import load_settings
    from app.application import ApplicationService

    settings = load_settings(base_dir=base_dir)
    use_gui = args.gui or (not args.headless and not settings.app.headless)

    service = ApplicationService(settings=settings, base_dir=base_dir)

    if use_gui:
        from ui.main_window import MainWindow

        window = MainWindow(service)
        window.run()
        return 0

    service.start()
    print("수집기 실행 중... Ctrl+C로 종료")
    try:
        import time

        while service.state.running:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
