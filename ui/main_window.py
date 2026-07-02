"""간단한 Tkinter 상태 UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.application import ApplicationService, ApplicationState


class MainWindow:
    """수집기 시작/중지 및 상태 표시."""

    def __init__(self, service: ApplicationService) -> None:
        self._service = service
        self._root = tk.Tk()
        self._root.title("Kakao Instagram Collector")
        self._root.geometry("420x260")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._status_var = tk.StringVar(value="대기 중")
        self._rooms_var = tk.StringVar(value="0")
        self._messages_var = tk.StringVar(value="0")
        self._saved_var = tk.StringVar(value="0")
        self._total_var = tk.StringVar(value=str(service.state.total_accounts))

        self._build()
        service.on_state_change(self._update_state)

    def _build(self) -> None:
        frame = ttk.Frame(self._root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="상태:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, textvariable=self._status_var).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frame, text="감시 채팅방:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._rooms_var).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(frame, text="처리 메시지:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._messages_var).grid(row=2, column=1, sticky=tk.W)

        ttk.Label(frame, text="신규 저장:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._saved_var).grid(row=3, column=1, sticky=tk.W)

        ttk.Label(frame, text="총 계정 수:").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Label(frame, textvariable=self._total_var).grid(row=4, column=1, sticky=tk.W)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=16)

        ttk.Button(btn_frame, text="시작", command=self._service.start).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="중지", command=self._service.stop).pack(side=tk.LEFT, padx=4)

        ttk.Label(
            frame,
            text="Windows + 카카오톡 PC 실행 후 오픈채팅방을 열어두세요.",
            wraplength=360,
        ).grid(row=6, column=0, columnspan=2, sticky=tk.W)

    def _update_state(self, state: ApplicationState) -> None:
        self._status_var.set("실행 중" if state.running else "대기 중")
        self._rooms_var.set(str(state.rooms))
        self._messages_var.set(str(state.messages_processed))
        self._saved_var.set(str(state.accounts_saved))
        self._total_var.set(str(state.total_accounts))

    def _on_close(self) -> None:
        self._service.stop()
        self._root.destroy()

    def run(self) -> None:
        self._root.mainloop()
