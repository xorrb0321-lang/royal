"""결과 출력: 로드뷰 링크 목록(CSV/TXT) + 지도 HTML.

강아지가 검출된 파노라마를 모아
- results.csv (좌표·촬영일·신뢰도·로드뷰 링크)
- roadview_links.txt (링크만, 신뢰도 내림차순)
- map.html (folium 지도; 핀 팝업에서 로드뷰 바로가기)
로 저장한다.
"""

from __future__ import annotations

import base64
import csv
import html
import io
import logging
from dataclasses import dataclass
from pathlib import Path

from .collect import PanoRecord
from .config import Config
from .detect import Detection

logger = logging.getLogger(__name__)


@dataclass
class DogSite:
    pano_id: str
    lat: float
    lon: float
    date: str | None
    dog_count: int
    max_confidence: float
    roadview_url: str | None
    best_image: str | None
    best_face: str | None


def aggregate(
    records: list[PanoRecord], detections: list[Detection]
) -> list[DogSite]:
    """파노라마별로 탐지 결과를 집계하여 강아지 발견 지점 목록 생성."""
    rec_by_id = {r.id: r for r in records}
    by_pano: dict[str, list[Detection]] = {}
    for det in detections:
        by_pano.setdefault(det.pano_id, []).append(det)

    sites: list[DogSite] = []
    for pano_id, dets in by_pano.items():
        rec = rec_by_id.get(pano_id)
        if rec is None:
            continue
        best = max(dets, key=lambda d: d.confidence)
        sites.append(
            DogSite(
                pano_id=pano_id,
                lat=rec.lat,
                lon=rec.lon,
                date=rec.date,
                dog_count=len(dets),
                max_confidence=best.confidence,
                roadview_url=rec.permalink,
                best_image=best.image_path,
                best_face=best.face,
            )
        )
    sites.sort(key=lambda s: s.max_confidence, reverse=True)
    return sites


def write_csv(sites: list[DogSite], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["pano_id", "date", "lat", "lon", "dog_count", "max_confidence", "roadview_url", "best_face"]
        )
        for s in sites:
            writer.writerow(
                [
                    s.pano_id,
                    s.date or "",
                    f"{s.lat:.6f}",
                    f"{s.lon:.6f}",
                    s.dog_count,
                    f"{s.max_confidence:.3f}",
                    s.roadview_url or "",
                    s.best_face or "",
                ]
            )
    logger.info("CSV 저장: %s (%d개 지점)", path, len(sites))


def write_links(sites: list[DogSite], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [s.roadview_url for s in sites if s.roadview_url]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    logger.info("링크 목록 저장: %s (%d개)", path, len(lines))


def _thumb_data_uri(image_path: str | None, bbox_hint: bool = False, size: int = 240) -> str | None:
    if not image_path or not Path(image_path).exists():
        return None
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img.thumbnail((size, size))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64}"
    except Exception:  # noqa: BLE001
        return None


def write_map(sites: list[DogSite], path: Path) -> None:
    if not sites:
        logger.info("발견 지점이 없어 지도를 생성하지 않습니다.")
        return
    try:
        import folium
    except Exception:  # noqa: BLE001
        logger.warning("folium 미설치로 지도 HTML을 건너뜁니다.")
        return

    center_lat = sum(s.lat for s in sites) / len(sites)
    center_lon = sum(s.lon for s in sites) / len(sites)
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="OpenStreetMap")

    for s in sites:
        thumb = _thumb_data_uri(s.best_image)
        parts = [f"<b>촬영일:</b> {html.escape(s.date or '미상')}<br>"]
        parts.append(f"<b>강아지 수:</b> {s.dog_count} · <b>신뢰도:</b> {s.max_confidence:.2f}<br>")
        if s.roadview_url:
            parts.append(
                f'<a href="{html.escape(s.roadview_url)}" target="_blank">네이버 로드뷰 바로가기</a><br>'
            )
        if thumb:
            parts.append(f'<img src="{thumb}" style="margin-top:6px;max-width:240px;">')
        popup = folium.Popup("".join(parts), max_width=260)
        folium.Marker(
            location=[s.lat, s.lon],
            popup=popup,
            tooltip=f"강아지 {s.dog_count}마리 ({s.max_confidence:.2f})",
            icon=folium.Icon(color="red", icon="paw", prefix="fa"),
        ).add_to(fmap)

    path.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(path))
    logger.info("지도 저장: %s", path)


def write_all(config: Config, sites: list[DogSite]) -> dict[str, Path]:
    run_dir = config.run_dir()
    csv_path = run_dir / "results.csv"
    links_path = run_dir / "roadview_links.txt"
    map_path = run_dir / "map.html"
    write_csv(sites, csv_path)
    write_links(sites, links_path)
    write_map(sites, map_path)
    return {"csv": csv_path, "links": links_path, "map": map_path}
