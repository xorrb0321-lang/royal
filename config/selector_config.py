"""UI Automation selector 설정."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DEFAULT_SELECTORS_PATH = Path(__file__).resolve().parent / "selectors.yaml"


@dataclass(frozen=True)
class ProcessSelector:
    """프로세스 selector."""

    name: str = "KakaoTalk.exe"


@dataclass(frozen=True)
class WindowSelector:
    """창 selector."""

    class_name: str = ""
    name_contains: str = ""
    name_excludes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WindowsSelector:
    """창 종류별 selector."""

    main: WindowSelector = field(default_factory=WindowSelector)
    chat_popup: WindowSelector = field(default_factory=WindowSelector)


@dataclass(frozen=True)
class MessageAreaSelector:
    """메시지 영역 selector."""

    control_type: str = "List"
    search_depth: int = 20


@dataclass(frozen=True)
class MessageItemSelector:
    """메시지 항목 selector."""

    control_type: str = "ListItem"


@dataclass(frozen=True)
class MessageTextSelector:
    """메시지 텍스트 노드 selector."""

    control_types: list[str] = field(default_factory=lambda: ["Text", "Hyperlink"])


@dataclass(frozen=True)
class SelectorConfig:
    """UI selector 루트."""

    process: ProcessSelector = field(default_factory=ProcessSelector)
    windows: WindowsSelector = field(default_factory=WindowsSelector)
    message_area: MessageAreaSelector = field(default_factory=MessageAreaSelector)
    message_item: MessageItemSelector = field(default_factory=MessageItemSelector)
    message_text: MessageTextSelector = field(default_factory=MessageTextSelector)


def _window_selector(data: dict) -> WindowSelector:
    return WindowSelector(
        class_name=data.get("class_name", ""),
        name_contains=data.get("name_contains", ""),
        name_excludes=list(data.get("name_excludes", [])),
    )


def load_selectors(path: Path | None = None) -> SelectorConfig:
    """YAML selector 파일 로드."""
    selectors_path = path or _DEFAULT_SELECTORS_PATH
    with selectors_path.open(encoding="utf-8") as fp:
        raw = yaml.safe_load(fp) or {}

    windows_raw = raw.get("windows", {})
    message_text_raw = raw.get("message_text", {})

    return SelectorConfig(
        process=ProcessSelector(**raw.get("process", {})),
        windows=WindowsSelector(
            main=_window_selector(windows_raw.get("main", {})),
            chat_popup=_window_selector(windows_raw.get("chat_popup", {})),
        ),
        message_area=MessageAreaSelector(**raw.get("message_area", {})),
        message_item=MessageItemSelector(**raw.get("message_item", {})),
        message_text=MessageTextSelector(
            control_types=list(
                message_text_raw.get("control_types", ["Text", "Hyperlink"])
            ),
        ),
    )
