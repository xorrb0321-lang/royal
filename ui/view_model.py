"""상태 ViewModel."""

from __future__ import annotations

from dataclasses import dataclass

from app.application import ApplicationService, ApplicationState


@dataclass
class StatusViewModel:
    """UI 표시용 상태."""

    running: bool
    rooms: int
    messages_processed: int
    accounts_saved: int
    total_accounts: int

    @classmethod
    def from_state(cls, state: ApplicationState) -> StatusViewModel:
        return cls(
            running=state.running,
            rooms=state.rooms,
            messages_processed=state.messages_processed,
            accounts_saved=state.accounts_saved,
            total_accounts=state.total_accounts,
        )

    @classmethod
    def bind(cls, service: ApplicationService) -> StatusViewModel:
        vm = cls.from_state(service.state)

        def on_change(state: ApplicationState) -> None:
            nonlocal vm
            vm = cls.from_state(state)

        service.on_state_change(on_change)
        return vm
