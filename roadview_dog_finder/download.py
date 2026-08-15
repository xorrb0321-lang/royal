"""파노라마를 큐브맵 면 이미지로 다운로드.

``streetlevel``의 큐브맵은 front, right, back, left, top, bottom 순서로 반환된다.
강아지는 지면 주변에 있으므로 기본적으로 측면 4개(front/right/back/left)만 저장한다.
이미 저장된 파노라마는 건너뛰어 이어받기가 된다.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .collect import PanoRecord, RateLimiter
from .config import Config

logger = logging.getLogger(__name__)

FACE_NAMES = ("front", "right", "back", "left", "top", "bottom")
SIDE_FACE_INDICES = (0, 1, 2, 3)


class PanoramaDownloader:
    def __init__(self, config: Config):
        self.config = config
        self.rate = RateLimiter(config.request_delay_s)

    def _face_indices(self) -> tuple[int, ...]:
        return SIDE_FACE_INDICES if self.config.side_faces_only else tuple(range(6))

    def _paths_for(self, pano_id: str) -> dict[int, Path]:
        base = self.config.images_dir() / pano_id
        return {i: base / f"{FACE_NAMES[i]}.jpg" for i in self._face_indices()}

    def _already_done(self, pano_id: str) -> bool:
        return all(p.exists() for p in self._paths_for(pano_id).values())

    def _fetch_faces(self, pano):
        from streetlevel import naver
        from streetlevel.util import CubemapStitchingMethod

        for attempt in range(1, self.config.max_retries + 1):
            self.rate.wait()
            try:
                faces = naver.get_panorama(
                    pano,
                    zoom=self.config.image_zoom,
                    stitching_method=CubemapStitchingMethod.NONE,
                )
                if isinstance(faces, list):
                    return faces
                return [faces]
            except Exception as exc:  # noqa: BLE001 - 네트워크 예외 재시도
                wait = self.config.retry_backoff_s * attempt
                logger.warning(
                    "이미지 다운로드 실패(%d/%d) pano=%s: %s -> %.1fs 후 재시도",
                    attempt,
                    self.config.max_retries,
                    pano.id,
                    exc,
                    wait,
                )
                time.sleep(wait)
        return None

    def download_one(self, rec: PanoRecord) -> list[Path]:
        """한 파노라마의 (측면) 면 이미지를 저장하고 경로 목록을 반환."""
        if self._already_done(rec.id):
            return list(self._paths_for(rec.id).values())

        from streetlevel import naver

        pano = naver.find_panorama_by_id(rec.id)
        if pano is None:
            logger.warning("파노라마 조회 실패로 건너뜀: %s", rec.id)
            return []

        faces = self._fetch_faces(pano)
        if not faces:
            return []

        out_paths: list[Path] = []
        targets = self._paths_for(rec.id)
        for idx, path in targets.items():
            if idx >= len(faces):
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            img = faces[idx]
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(path, quality=90)
            out_paths.append(path)
        return out_paths

    def download_all(self, records: list[PanoRecord]) -> dict[str, list[Path]]:
        result: dict[str, list[Path]] = {}
        total = len(records)
        for i, rec in enumerate(records, start=1):
            if i % 20 == 0 or i == total:
                logger.info("이미지 다운로드 %d/%d", i, total)
            paths = self.download_one(rec)
            if paths:
                result[rec.id] = paths
        logger.info("다운로드 완료: %d개 파노라마", len(result))
        return result


def collect_existing_images(config: Config, records: list[PanoRecord]) -> dict[str, list[Path]]:
    """이미 저장된 이미지 경로만 모아서 반환(다운로드 없이 탐지만 할 때 사용)."""
    out: dict[str, list[Path]] = {}
    for rec in records:
        base = config.images_dir() / rec.id
        if base.exists():
            imgs = sorted(base.glob("*.jpg"))
            if imgs:
                out[rec.id] = imgs
    return out
