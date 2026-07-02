"""UI ViewModel."""

from __future__ import annotations

from dataclasses import dataclass

from app.application import ApplicationService, ApplicationState


@dataclass
class StatusViewModel:
    running: bool
    files_processed: int
    total_accounts: int
    new_accounts: int
    duplicates_skipped: int
    watch_dir: str
    csv_path: str

    @classmethod
    def from_state(cls, state: ApplicationState) -> StatusViewModel:
        return cls(
            running=state.running,
            files_processed=state.files_processed,
            total_accounts=state.total_accounts,
            new_accounts=state.new_accounts,
            duplicates_skipped=state.duplicates_skipped,
            watch_dir=state.watch_dir,
            csv_path=state.csv_path,
        )

    @classmethod
    def bind(cls, service: ApplicationService) -> StatusViewModel:
        vm = cls.from_state(service.state)

        def on_change(state: ApplicationState) -> None:
            nonlocal vm
            vm = cls.from_state(state)

        service.on_state_change(on_change)
        return vm
