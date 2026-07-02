"""KakaoTalk 분할 export 파일 병합."""

from __future__ import annotations

import re
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

_SPLIT_SUFFIX = re.compile(r"^(.+?)\s*\((\d+)\)$")


class SplitFileMerger:
    """1MB 분할 txt (예: file (1).txt) 그룹화."""

    def group_export_sets(self, files: list[Path]) -> list[list[Path]]:
        """동일 대화의 분할 파일을 그룹으로 묶음."""
        groups: dict[str, list[tuple[int, Path]]] = {}
        for path in files:
            stem = path.stem
            match = _SPLIT_SUFFIX.match(stem)
            if match:
                base, idx = match.group(1), int(match.group(2))
                groups.setdefault(base, []).append((idx, path))
            else:
                groups.setdefault(stem, []).append((0, path))

        result: list[list[Path]] = []
        for items in groups.values():
            ordered = [p for _, p in sorted(items, key=lambda x: x[0])]
            result.append(ordered)
        result.sort(key=lambda g: g[0].stat().st_mtime)
        return result

    def pick_primary(self, group: list[Path]) -> Path:
        """처리 대표 파일 (첫 분할)."""
        return group[0]

    def should_process_group(self, group: list[Path], processed_hashes: set[str]) -> bool:
        """그룹 내 모든 파일 해시가 이미 처리됐으면 스킵."""
        import hashlib

        combined = hashlib.sha256()
        for path in group:
            combined.update(path.read_bytes())
        group_hash = combined.hexdigest()
        return group_hash not in processed_hashes

    def group_hash(self, group: list[Path]) -> str:
        import hashlib

        combined = hashlib.sha256()
        for path in group:
            combined.update(path.read_bytes())
        return combined.hexdigest()
