"""CLI 오케스트레이션.

단계(stage)를 순서대로 실행하며, 각 단계 결과를 작업 폴더에 저장해 이어받기가 된다.

  area    : 경계 + 도로망(큰길 제외) + 좌표 샘플링
  collect : streetlevel로 파노라마 수집 + 촬영일/최신 필터
  download: 큐브맵 측면 이미지 다운로드
  detect  : YOLO 강아지 탐지
  report  : 로드뷰 링크 목록(CSV/TXT) + 지도 HTML

예)
  python -m roadview_dog_finder.run --place "전라남도 해남군 ...리" --output-dir /mnt/d/rdf
  python -m roadview_dog_finder.run --center 34.5 126.6 --radius 800 --output-dir /mnt/d/rdf
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from .config import Config, AreaSpec
from .collect import PanoRecord, PanoramaCollector, load_records

logger = logging.getLogger(__name__)

ALL_STAGES = ["area", "collect", "download", "detect", "report"]


# --------------------------------------------------------------------------- #
# 단계별 결과 입출력
# --------------------------------------------------------------------------- #
def _points_path(config: Config) -> Path:
    return config.run_dir() / "area_points.json"


def _roads_path(config: Config) -> Path:
    return config.run_dir() / "roads.json"


def _panos_path(config: Config) -> Path:
    return config.run_dir() / "panoramas.jsonl"


def _detections_path(config: Config) -> Path:
    return config.run_dir() / "detections.jsonl"


def save_points(config: Config, points: list[tuple[float, float]]) -> None:
    p = _points_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(points), encoding="utf-8")


def load_points(config: Config) -> list[tuple[float, float]]:
    p = _points_path(config)
    if not p.exists():
        return []
    return [tuple(x) for x in json.loads(p.read_text(encoding="utf-8"))]


def save_roads(config: Config, lines) -> None:
    p = _roads_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    coords = [list(ln.coords) for ln in lines]
    p.write_text(json.dumps(coords), encoding="utf-8")


def load_roads(config: Config):
    from shapely.geometry import LineString

    p = _roads_path(config)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return [LineString(c) for c in data if len(c) >= 2]


# --------------------------------------------------------------------------- #
# 단계 실행
# --------------------------------------------------------------------------- #
def stage_area(config: Config) -> None:
    from .area import build_area

    _, lines, points = build_area(config)
    save_roads(config, lines)
    save_points(config, points)
    logger.info("[area] 좌표 %d개 저장", len(points))


def stage_collect(config: Config) -> None:
    points = load_points(config)
    if not points:
        logger.warning("[collect] 샘플 좌표가 없습니다. 먼저 area 단계를 실행하세요.")
        return
    lines = load_roads(config)
    collector = PanoramaCollector(config, road_lines=lines)

    # 경계 폴리곤도 필터에 사용(있으면)
    polygon = None
    try:
        from .area import get_boundary_polygon

        polygon = get_boundary_polygon(config)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[collect] 경계 폴리곤 재구성 실패(무시): %s", exc)

    records = collector.collect(points, _panos_path(config), polygon=polygon)
    logger.info("[collect] 파노라마 %d개", len(records))


def stage_download(config: Config, limit: int | None) -> None:
    from .download import PanoramaDownloader

    records = load_records(_panos_path(config))
    if limit:
        records = records[:limit]
    if not records:
        logger.warning("[download] 수집된 파노라마가 없습니다.")
        return
    PanoramaDownloader(config).download_all(records)


def stage_detect(config: Config, limit: int | None) -> None:
    from .detect import DogDetector
    from .download import collect_existing_images

    records = load_records(_panos_path(config))
    if limit:
        records = records[:limit]
    images = collect_existing_images(config, records)
    if not images:
        logger.warning("[detect] 탐지할 이미지가 없습니다. 먼저 download 단계를 실행하세요.")
        return

    detector = DogDetector(config)
    detections = detector.detect_batch(images)

    out = _detections_path(config)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for det in detections:
            fh.write(json.dumps(asdict(det), ensure_ascii=False) + "\n")
    logger.info("[detect] 탐지 결과 저장: %s", out)


def stage_report(config: Config) -> None:
    from .detect import Detection
    from .report import aggregate, write_all

    records = load_records(_panos_path(config))
    dpath = _detections_path(config)
    detections: list[Detection] = []
    if dpath.exists():
        for line in dpath.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                data["bbox"] = tuple(data["bbox"])
                detections.append(Detection(**data))

    sites = aggregate(records, detections)
    paths = write_all(config, sites)
    logger.info("[report] 완료. 강아지 발견 지점 %d곳", len(sites))
    logger.info("[report] 결과: %s", paths["csv"])
    logger.info("[report] 링크: %s", paths["links"])
    logger.info("[report] 지도: %s", paths["map"])


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_config(args: argparse.Namespace) -> Config:
    area = AreaSpec(
        place=args.place,
        bbox=tuple(args.bbox) if args.bbox else None,
        center=tuple(args.center) if args.center else None,
        radius_m=args.radius,
        geojson=args.geojson,
    )
    config = Config(area=area)
    if args.output_dir:
        config.output_dir = Path(args.output_dir)
    if args.sample_interval is not None:
        config.sample_interval_m = args.sample_interval
    if args.max_age_years is not None:
        config.max_age_years = args.max_age_years
    if args.expand_neighbors:
        config.expand_neighbors = True
    if args.request_delay is not None:
        config.request_delay_s = args.request_delay
    if args.image_zoom is not None:
        config.image_zoom = args.image_zoom
    if args.all_faces:
        config.side_faces_only = False
    if args.model:
        config.yolo_model = args.model
    if args.conf is not None:
        config.dog_conf_threshold = args.conf
    if args.device:
        config.device = args.device
    return config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="roadview_dog_finder",
        description="네이버 로드뷰에서 강아지 지점을 찾아 로드뷰 링크로 뽑아주는 도구",
    )
    # 대상 지역(하나 선택)
    g = p.add_argument_group("대상 지역")
    g.add_argument("--place", help="지명(OSM 지오코딩). 예: '전라남도 해남군 ...리'")
    g.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("MIN_LAT", "MIN_LON", "MAX_LAT", "MAX_LON"),
        help="사각 범위",
    )
    g.add_argument("--center", nargs=2, type=float, metavar=("LAT", "LON"), help="원형 범위 중심")
    g.add_argument("--radius", type=float, help="원형 범위 반경(미터)")
    g.add_argument("--geojson", help="경계 폴리곤 GeoJSON 파일 경로")

    # 파이프라인 옵션
    o = p.add_argument_group("옵션")
    o.add_argument("--output-dir", help="작업/결과 폴더(외장 드라이브 권장)")
    o.add_argument("--sample-interval", type=float, help="좌표 샘플 간격(미터, 기본 10)")
    o.add_argument("--max-age-years", type=float, help="촬영일 최대 경과 연수(기본 4)")
    o.add_argument("--expand-neighbors", action="store_true", help="인접 파노라마까지 확장 수집")
    o.add_argument("--request-delay", type=float, help="요청 간격(초, 기본 0.7)")
    o.add_argument("--image-zoom", type=int, help="이미지 해상도 0~2(기본 1)")
    o.add_argument("--all-faces", action="store_true", help="측면 4개 대신 6개 면 모두 사용")
    o.add_argument("--model", help="YOLO 모델(기본 yolov8n.pt)")
    o.add_argument("--conf", type=float, help="강아지 탐지 신뢰도 임계값(기본 0.25)")
    o.add_argument("--device", help="탐지 디바이스(cuda:0/cpu, 기본 자동)")
    o.add_argument(
        "--stages",
        default="all",
        help="실행 단계 콤마구분(area,collect,download,detect,report) 또는 all",
    )
    o.add_argument("--limit", type=int, help="파노라마 처리 개수 제한(파일럿/테스트용)")
    o.add_argument("--verbose", action="store_true", help="상세 로그")

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = build_config(args)

    stages = ALL_STAGES if args.stages == "all" else [s.strip() for s in args.stages.split(",")]
    invalid = [s for s in stages if s not in ALL_STAGES]
    if invalid:
        logger.error("알 수 없는 단계: %s (가능: %s)", invalid, ALL_STAGES)
        return 2

    logger.info("대상 지역: %s", config.area.label())
    logger.info("작업 폴더: %s", config.run_dir())
    logger.info("실행 단계: %s", stages)

    try:
        if "area" in stages:
            stage_area(config)
        if "collect" in stages:
            stage_collect(config)
        if "download" in stages:
            stage_download(config, args.limit)
        if "detect" in stages:
            stage_detect(config, args.limit)
        if "report" in stages:
            stage_report(config)
    except KeyboardInterrupt:
        logger.warning("사용자 중단. 지금까지의 진행은 저장되어 있어 이어받기가 가능합니다.")
        return 130
    except Exception as exc:  # noqa: BLE001
        logger.exception("실행 실패: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
