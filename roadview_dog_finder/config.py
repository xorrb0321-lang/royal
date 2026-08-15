"""파이프라인 전역 설정.

대상 지역, 도로 필터, 촬영일 필터, 저장 경로, 요청 간격(rate limit),
탐지 임계값 등을 한곳에서 관리한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# OSM `highway` 태그 중 "큰길"로 간주하여 제외할 등급.
# 마을 안길·농로만 남기기 위해 고속/국도/주요 간선(및 그 램프)을 제외한다.
DEFAULT_EXCLUDED_HIGHWAYS: tuple[str, ...] = (
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
)

# COCO 데이터셋에서 "dog" 클래스 인덱스(YOLOv8 기본 가중치 기준).
COCO_DOG_CLASS_ID = 16


@dataclass
class AreaSpec:
    """대상 지역 지정 방법.

    아래 중 하나만 채우면 된다(우선순위: geojson > place > bbox > center+radius).

    - ``place``: 지명 문자열(예: "전라남도 해남군 ...리"). OSM 지오코딩으로 경계를 얻는다.
    - ``bbox``: (min_lat, min_lon, max_lat, max_lon) 사각 범위.
    - ``center`` + ``radius_m``: 중심 좌표(lat, lon)와 반경(미터)로 원형 범위.
    - ``geojson``: 경계 폴리곤이 담긴 GeoJSON 파일 경로.
    """

    place: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    center: tuple[float, float] | None = None
    radius_m: float | None = None
    geojson: str | None = None

    def label(self) -> str:
        if self.geojson:
            return f"geojson:{Path(self.geojson).stem}"
        if self.place:
            return self.place
        if self.bbox:
            return "bbox:" + ",".join(f"{v:.4f}" for v in self.bbox)
        if self.center and self.radius_m:
            return f"circle:{self.center[0]:.4f},{self.center[1]:.4f},{self.radius_m:.0f}m"
        return "unknown-area"


@dataclass
class Config:
    # --- 대상 지역 ---
    area: AreaSpec = field(default_factory=AreaSpec)

    # --- 도로 필터 ---
    excluded_highways: tuple[str, ...] = DEFAULT_EXCLUDED_HIGHWAYS
    # 도로를 따라 파노라마를 찾을 좌표 샘플 간격(미터). 로드뷰 지점이 보통
    # 5~10m 간격이라 10m면 대부분 지점을 놓치지 않고 중복 제거로 정리된다.
    sample_interval_m: float = 10.0
    # 인접 파노라마(neighbors) 링크를 따라 추가 확장할지 여부.
    # True면 커버리지가 좋아지지만 요청 수가 늘어난다.
    expand_neighbors: bool = False
    # 확장 시, 유지된 도로에서 이 거리(미터) 이내의 파노라마만 채택(큰길 침범 방지).
    road_buffer_m: float = 25.0

    # --- 촬영일 필터 ---
    max_age_years: float = 4.0
    # 같은 지점의 여러 시점 중 최신 파노라마만 사용할지 여부.
    latest_only: bool = True

    # --- 네트워크(예의상 저부하 운영) ---
    request_delay_s: float = 0.7  # 요청 사이 최소 대기(초)
    max_retries: int = 3
    retry_backoff_s: float = 2.0
    request_timeout_s: float = 20.0

    # --- 이미지 다운로드 ---
    # 0=저해상, 2=고해상. 탐지에는 1이면 충분하고 빠르며 저장공간도 아낀다.
    image_zoom: int = 1
    # 위/아래(하늘·차량 가림) 큐브맵 면은 강아지가 없으므로 측면 4개만 저장/탐지.
    side_faces_only: bool = True

    # --- 탐지 ---
    yolo_model: str = "yolov8n.pt"  # 자동 다운로드되는 경량 모델
    dog_conf_threshold: float = 0.25
    dog_class_id: int = COCO_DOG_CLASS_ID
    device: str | None = None  # None=자동(GPU 있으면 cuda, 없으면 cpu)
    detect_batch_size: int = 16

    # --- 저장 경로 ---
    # 결과/이미지가 쌓일 작업 폴더. 외장 드라이브 경로를 지정하는 것을 권장.
    output_dir: Path = Path("./rdf_output")

    def run_dir(self) -> Path:
        """이 실행의 결과가 저장될 폴더(지역 라벨 기반)."""
        safe = _slugify(self.area.label())
        return self.output_dir / safe

    def images_dir(self) -> Path:
        return self.run_dir() / "images"

    def cutoff_iso(self) -> str:
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=365.25 * self.max_age_years)
        return cutoff.isoformat()


def _slugify(text: str) -> str:
    keep = []
    for ch in text:
        if ch.isalnum() or ch in "-_.":
            keep.append(ch)
        elif ch in " /:,":
            keep.append("_")
    slug = "".join(keep).strip("_")
    return slug or "area"
