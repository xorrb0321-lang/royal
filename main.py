"""카카오톡 export → Instagram 수집기."""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KakaoTalk export txt → Instagram username collector",
    )
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--gui", action="store_true", help="Tkinter GUI")
    parser.add_argument("--headless", action="store_true", help="콘솔 모드")
    parser.add_argument("--file", type=Path, action="append", help="처리할 txt 파일")
    parser.add_argument("--scan-once", action="store_true", help="exports 폴더 1회 스캔 후 종료")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir = args.base_dir.resolve()

    from config.settings import load_settings
    from app.application import ApplicationService

    settings = load_settings(base_dir=base_dir)
    service = ApplicationService(settings=settings, base_dir=base_dir)

    if args.file:
        for f in args.file:
            result = service.process_file(f.resolve())
            print(f"처리: {f.name} → 신규 {result.stats.new_accounts}건")
        service.reexport_csv()
        return 0

    if args.scan_once:
        service.start()
        time.sleep(2)
        service.stop()
        print(f"완료. CSV: {service.state.csv_path}")
        return 0

    use_gui = args.gui or not args.headless
    if use_gui:
        from ui.main_window import MainWindow

        MainWindow(service).run()
        return 0

    service.start()
    print(f"감시 중: {service.state.watch_dir}")
    print("Ctrl+C 종료")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
