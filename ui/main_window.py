"""Tkinter GUI."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from app.application import ApplicationService, ApplicationState


class MainWindow:
    """폴더 감시 + 드래그앤드롭(파일 선택) UI."""

    def __init__(self, service: ApplicationService) -> None:
        self._service = service
        self._root = tk.Tk()
        self._root.title("Kakao Instagram Collector")
        self._root.geometry("520x420")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._status_var = tk.StringVar(value="대기 중")
        self._watch_var = tk.StringVar(value=service.state.watch_dir)
        self._files_var = tk.StringVar(value="0")
        self._accounts_var = tk.StringVar(value=str(service.state.total_accounts))
        self._new_var = tk.StringVar(value="0")
        self._dup_var = tk.StringVar(value="0")
        self._csv_var = tk.StringVar(value=service.state.csv_path)

        self._build()
        service.on_state_change(self._update_state)
        self._service.start()

    def _build(self) -> None:
        frame = ttk.Frame(self._root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="상태:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, textvariable=self._status_var).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frame, text="감시 폴더:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._watch_var, wraplength=360).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(frame, text="처리 파일:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._files_var).grid(row=2, column=1, sticky=tk.W)

        ttk.Label(frame, text="Instagram 계정:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._accounts_var).grid(row=3, column=1, sticky=tk.W)

        ttk.Label(frame, text="신규 저장:").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._new_var).grid(row=4, column=1, sticky=tk.W)

        ttk.Label(frame, text="중복 스킵:").grid(row=5, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._dup_var).grid(row=5, column=1, sticky=tk.W)

        drop = ttk.LabelFrame(frame, text="수동 처리", padding=12)
        drop.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=12)
        ttk.Label(
            drop,
            text="카카오톡 대화보내기 .txt 파일을 선택하세요",
            wraplength=420,
        ).pack()
        ttk.Button(drop, text="txt 파일 선택", command=self._pick_files).pack(pady=8)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="CSV 열기", command=self._open_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="exports 폴더 열기", command=self._open_exports).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="중지", command=self._service.stop).pack(side=tk.LEFT, padx=4)

        ttk.Label(
            frame,
            text="사용법: 카카오톡 Ctrl+S 보내기 → exports 폴더 저장 → 자동 처리",
            wraplength=460,
        ).grid(row=8, column=0, columnspan=2, sticky=tk.W)

    def _pick_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="카카오톡 export txt 선택",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if paths:
            self._service.process_drop_paths([Path(p) for p in paths])

    def _open_csv(self) -> None:
        path = Path(self._csv_var.get())
        if path.exists():
            self._open_path(path.parent)

    def _open_exports(self) -> None:
        self._open_path(Path(self._watch_var.get()))

    def _open_path(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

    def _update_state(self, state: ApplicationState) -> None:
        self._status_var.set("실행 중" if state.running else "대기 중")
        self._files_var.set(str(state.files_processed))
        self._accounts_var.set(str(state.total_accounts))
        self._new_var.set(str(state.new_accounts))
        self._dup_var.set(str(state.duplicates_skipped))
        self._csv_var.set(state.csv_path)

    def _on_close(self) -> None:
        self._service.stop()
        self._root.destroy()

    def run(self) -> None:
        self._root.mainloop()
