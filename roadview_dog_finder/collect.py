"""네이버 파노라마 수집 + 촬영일/최신 필터.

샘플 좌표마다 ``streetlevel``로 가장 가까운 파노라마를 찾고,
촬영일(최근 N년) + 최신여부 필터를 통과한 것만 panoId 기준으로 중복 없이 모은다.
필요 시 인접 파노라마(neighbors) 링크를 따라 확장하되, 유지된 도로 근처만 채택해
큰길로 새는 것을 막는다.

모든 요청은 요청 간격 조절(rate limit)과 재시도로 저부하 운영한다.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import transform as shp_transform

from .config import Config
from .geo import LocalProjector

logger = logging.getLogger(__name__)


@dataclass
class PanoRecord:
    id: str
    lat: float
    lon: float
    date: str | None
    is_latest: bool | None
    title: str | None
    description: str | None
    permalink: str | None

    @staticmethod
    def from_pano(pano) -> "PanoRecord":
        return PanoRecord(
            id=str(pano.id),
            lat=float(pano.lat),
            lon=float(pano.lon),
            date=_date_iso(getattr(pano, "date", None)),
            is_latest=getattr(pano, "is_latest", None),
            title=getattr(pano, "title", None),
            description=getattr(pano, "description", None),
            permalink=_safe_permalink(pano),
        )


def _date_iso(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)


def _safe_permalink(pano) -> str | None:
    try:
        return pano.permalink()
    except Exception:  # noqa: BLE001 - permalink 실패는 치명적이지 않음
        try:
            from streetlevel import naver

            return naver.build_permalink(pano.id)
        except Exception:  # noqa: BLE001
            return None


def _to_aware(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class RateLimiter:
    def __init__(self, delay_s: float):
        self.delay_s = delay_s
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        if elapsed < self.delay_s:
            time.sleep(self.delay_s - elapsed)
        self._last = time.monotonic()


class PanoramaCollector:
    def __init__(self, config: Config, road_lines: list[LineString] | None = None):
        self.config = config
        self.rate = RateLimiter(config.request_delay_s)
        self._roads_m: MultiLineString | None = None
        self._proj: LocalProjector | None = None
        if road_lines:
            self._build_road_index(road_lines)

    def _build_road_index(self, lines: list[LineString]) -> None:
        ref = lines[0].coords[0]
        self._proj = LocalProjector(ref[0], ref[1])
        projected = [
            shp_transform(lambda xs, ys, z=None: self._proj.to_m(xs, ys), ln) for ln in lines
        ]
        self._roads_m = MultiLineString(projected)

    def _near_road(self, lat: float, lon: float) -> bool:
        if self._roads_m is None or self._proj is None:
            return True
        x, y = self._proj.to_m(lon, lat)
        return self._roads_m.distance(Point(x, y)) <= self.config.road_buffer_m

    # --- streetlevel 호출 래퍼(재시도 + rate limit) ---
    def _find(self, lat: float, lon: float):
        from streetlevel import naver

        return self._with_retry(lambda: naver.find_panorama(lat, lon))

    def _find_by_id(self, pano_id: str):
        from streetlevel import naver

        return self._with_retry(lambda: naver.find_panorama_by_id(pano_id))

    def _with_retry(self, fn):
        last_exc: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            self.rate.wait()
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 - 네트워크 예외 재시도
                last_exc = exc
                wait = self.config.retry_backoff_s * attempt
                logger.warning("요청 실패(%d/%d): %s -> %.1fs 후 재시도", attempt, self.config.max_retries, exc, wait)
                time.sleep(wait)
        logger.error("요청 최종 실패: %s", last_exc)
        return None

    def _passes_filters(self, rec: PanoRecord) -> bool:
        if self.config.latest_only and rec.is_latest is False:
            return False
        dt = _to_aware(rec.date)
        if dt is None:
            return False  # 촬영일 미상은 제외(4년 필터 보증 불가)
        cutoff = _to_aware(self.config.cutoff_iso())
        return dt >= cutoff

    def collect(
        self,
        points: list[tuple[float, float]],
        out_path: Path,
        polygon=None,
    ) -> list[PanoRecord]:
        """샘플 좌표에서 파노라마를 수집하여 jsonl로 저장하고 리스트로 반환.

        out_path가 이미 존재하면 그 안의 panoId는 건너뛰어 이어받기가 된다.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)
        accepted: dict[str, PanoRecord] = {}
        visited: set[str] = set()

        # 이어받기: 기존 결과 로드
        if out_path.exists():
            for line in out_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                rec = PanoRecord(**data)
                accepted[rec.id] = rec
                visited.add(rec.id)
            logger.info("이어받기: 기존 %d개 파노라마 로드", len(accepted))

        queue: deque[tuple[str, object]] = deque()
        for lat, lon in points:
            queue.append(("coord", (lat, lon)))

        total_seeds = len(points)
        processed = 0

        with out_path.open("a", encoding="utf-8") as fh:
            while queue:
                kind, payload = queue.popleft()
                if kind == "coord":
                    processed += 1
                    if processed % 25 == 0:
                        logger.info(
                            "진행 %d/%d 좌표 · 채택 %d개", processed, total_seeds, len(accepted)
                        )
                    lat, lon = payload  # type: ignore[misc]
                    pano = self._find(lat, lon)
                else:  # "id"
                    pano_id = payload  # type: ignore[assignment]
                    if pano_id in visited:
                        continue
                    pano = self._find_by_id(pano_id)  # type: ignore[arg-type]

                if pano is None:
                    continue
                pid = str(pano.id)
                if pid in visited:
                    continue
                visited.add(pid)

                if polygon is not None and not polygon.covers(Point(pano.lon, pano.lat)):
                    continue
                if not self._near_road(pano.lat, pano.lon):
                    continue

                rec = PanoRecord.from_pano(pano)
                if self._passes_filters(rec):
                    if pid not in accepted:
                        accepted[pid] = rec
                        fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
                        fh.flush()

                if self.config.expand_neighbors:
                    for nb in _street_neighbors(pano):
                        nb_id = str(nb.id)
                        if nb_id not in visited and self._near_road(nb.lat, nb.lon):
                            queue.append(("id", nb_id))

        logger.info("수집 완료: %d개 파노라마(필터 통과)", len(accepted))
        return list(accepted.values())


def _street_neighbors(pano) -> list:
    neighbors = getattr(pano, "neighbors", None)
    if neighbors is None:
        return []
    street = getattr(neighbors, "street", None)
    return list(street) if street else []


def load_records(path: Path) -> list[PanoRecord]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(PanoRecord(**json.loads(line)))
    return out
