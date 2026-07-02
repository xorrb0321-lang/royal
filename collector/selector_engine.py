"""UI selector 기반 element 탐색."""

from __future__ import annotations

import sys
from typing import Any

from config.selector_config import SelectorConfig
from utils.logger import get_logger
from utils.retry import RetryPolicy

logger = get_logger(__name__)


class SelectorEngine:
    """selectors.yaml 기반 UIA 탐색."""

    def __init__(self, selectors: SelectorConfig, retry: RetryPolicy) -> None:
        self._selectors = selectors
        self._retry = retry
        self._uia = None
        if sys.platform == "win32":
            import uiautomation as uia

            self._uia = uia

    @property
    def available(self) -> bool:
        return self._uia is not None

    def get_root_by_pid(self, pid: int) -> Any | None:
        """프로세스 루트 엘리먼트."""
        if not self.available:
            return None

        def _find() -> Any:
            root = self._uia.GetRootControl()
            for window in root.GetChildren():
                try:
                    if window.ProcessId == pid:
                        return window
                except Exception:
                    continue
            return self._uia.WindowControl(searchDepth=1, ProcessId=pid)

        try:
            return self._retry.run(_find)
        except Exception as exc:
            logger.error("UI Element 접근 실패 (root): %s", exc)
            return None

    def find_chat_windows(self, pid: int) -> list[Any]:
        """채팅방 창 목록 탐색."""
        if not self.available:
            return []

        popup_cfg = self._selectors.windows.chat_popup
        main_cfg = self._selectors.windows.main
        windows: list[Any] = []

        def _collect() -> list[Any]:
            found: list[Any] = []
            root = self._uia.GetRootControl()
            for control in root.GetChildren():
                try:
                    if control.ProcessId != pid:
                        continue
                    if control.ControlTypeName != "WindowControl":
                        continue
                    name = (control.Name or "").strip()
                    if not name:
                        continue
                    # 메인 카카오톡 창 제외
                    if main_cfg.name_contains and name == main_cfg.name_contains:
                        continue
                    if popup_cfg.name_excludes and name in popup_cfg.name_excludes:
                        continue
                    found.append(control)
                except Exception:
                    continue
            return found

        try:
            windows = self._retry.run(_collect)
        except Exception as exc:
            logger.error("UI Element 접근 실패 (chat windows): %s", exc)
        return windows

    def find_message_container(self, window: Any) -> Any | None:
        """메시지 리스트 컨테이너."""
        if not self.available:
            return None

        cfg = self._selectors.message_area

        def _find() -> Any | None:
            control_type = getattr(self._uia, f"{cfg.control_type}Control", None)
            if control_type is None:
                return window.Control(searchDepth=cfg.search_depth, ControlTypeName="ListControl")
            return control_type(searchDepth=cfg.search_depth, parent=window)

        try:
            container = self._retry.run(_find)
            if container and container.Exists(0, 0):
                return container
        except Exception as exc:
            logger.error("UI Element 접근 실패 (message container): %s", exc)
        return None

    def iter_message_items(self, container: Any) -> list[Any]:
        """메시지 ListItem 목록."""
        if not self.available or container is None:
            return []

        item_type = self._selectors.message_item.control_type

        try:
            children = container.GetChildren()
            return [
                child
                for child in children
                if child.ControlTypeName == f"{item_type}Control"
                or child.ControlTypeName.endswith("ItemControl")
            ]
        except Exception as exc:
            logger.error("UI Element 접근 실패 (message items): %s", exc)
            return []
