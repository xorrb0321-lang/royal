"""대상 지역 경계 + 도로망(큰길 제외) + 좌표 샘플링.

1) 리/읍 경계 폴리곤을 확보하고
2) 그 안의 도로망을 OSM에서 가져와 큰길 등급을 제외한 뒤
3) 남은 마을 안길·농로를 따라 일정 간격으로 좌표를 샘플링한다.

OSM 접근(osmnx)은 네트워크가 필요하므로 함수 안에서 지연 임포트한다.
샘플링 로직 자체는 순수 기하 연산이라 오프라인 테스트가 가능하다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, Point, Polygon, box, shape
from shapely.ops import transform as shp_transform

from .config import Config
from .geo import LocalProjector

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 경계 폴리곤
# --------------------------------------------------------------------------- #
def get_boundary_polygon(config: Config) -> Polygon:
    """설정에 맞는 경계 폴리곤(EPSG:4326)을 반환."""
    area = config.area

    if area.geojson:
        return _polygon_from_geojson(Path(area.geojson))

    if area.place:
        return _polygon_from_place(area.place)

    if area.bbox:
        min_lat, min_lon, max_lat, max_lon = area.bbox
        return box(min_lon, min_lat, max_lon, max_lat)

    if area.center and area.radius_m:
        return _circle_polygon(area.center[0], area.center[1], area.radius_m)

    raise ValueError(
        "대상 지역이 지정되지 않았습니다. place / bbox / center+radius / geojson 중 하나를 지정하세요."
    )


def _polygon_from_geojson(path: Path) -> Polygon:
    data = json.loads(path.read_text(encoding="utf-8"))
    geoms = []
    if data.get("type") == "FeatureCollection":
        for feat in data["features"]:
            geoms.append(shape(feat["geometry"]))
    elif data.get("type") == "Feature":
        geoms.append(shape(data["geometry"]))
    else:
        geoms.append(shape(data))
    merged = geoms[0]
    for g in geoms[1:]:
        merged = merged.union(g)
    if merged.geom_type == "MultiPolygon":
        merged = max(merged.geoms, key=lambda g: g.area)
    if not isinstance(merged, Polygon):
        raise ValueError(f"GeoJSON에서 폴리곤을 찾지 못했습니다: {path}")
    return merged


def _polygon_from_place(place: str) -> Polygon:
    import osmnx as ox  # 지연 임포트(네트워크 필요)

    logger.info("OSM 지오코딩으로 경계 조회: %s", place)
    gdf = ox.geocode_to_gdf(place)
    geom = gdf.unary_union
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    if not isinstance(geom, Polygon):
        raise ValueError(f"지명에서 폴리곤 경계를 얻지 못했습니다: {place}")
    return geom


def _circle_polygon(lat: float, lon: float, radius_m: float) -> Polygon:
    proj = LocalProjector(lon, lat)
    cx, cy = proj.to_m(lon, lat)
    circle_m = Point(cx, cy).buffer(radius_m, quad_segs=64)
    return shp_transform(lambda xs, ys, z=None: proj.to_deg(xs, ys), circle_m)


# --------------------------------------------------------------------------- #
# 도로망(큰길 제외)
# --------------------------------------------------------------------------- #
def get_road_lines(polygon: Polygon, config: Config) -> list[LineString]:
    """경계 내 도로(큰길 제외) 라인 목록(EPSG:4326)."""
    import osmnx as ox  # 지연 임포트

    logger.info("OSM 도로망 조회 중...")
    # network_type='drive'는 보행자 전용길(footway 등)을 자동 제외한다.
    graph = ox.graph_from_polygon(
        polygon, network_type="drive", simplify=True, retain_all=True, truncate_by_edge=True
    )
    edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)

    excluded = set(config.excluded_highways)
    lines: list[LineString] = []
    for geom, highway in zip(edges.geometry, edges.get("highway", [None] * len(edges))):
        if geom is None or geom.is_empty:
            continue
        if _is_excluded(highway, excluded):
            continue
        clipped = geom.intersection(polygon)
        _extend_lines(lines, clipped)

    logger.info("유지된 도로 세그먼트: %d개", len(lines))
    return lines


def _is_excluded(highway, excluded: set[str]) -> bool:
    """highway 태그(문자열 또는 리스트)가 제외 대상인지 판단.

    리스트인 경우 하나라도 유지 가능 등급이면 유지한다(보수적으로 포함).
    """
    if highway is None:
        return False
    if isinstance(highway, (list, tuple)):
        return all(h in excluded for h in highway)
    return highway in excluded


def _extend_lines(acc: list[LineString], geom) -> None:
    if geom.is_empty:
        return
    if isinstance(geom, LineString):
        acc.append(geom)
    elif isinstance(geom, MultiLineString):
        acc.extend(g for g in geom.geoms if not g.is_empty)


# --------------------------------------------------------------------------- #
# 좌표 샘플링(순수 기하 · 오프라인 테스트 가능)
# --------------------------------------------------------------------------- #
def sample_points_along_lines(
    lines: list[LineString], interval_m: float, polygon: Polygon | None = None
) -> list[tuple[float, float]]:
    """도로 라인을 따라 ``interval_m`` 간격으로 (lat, lon) 좌표를 생성.

    미터 단위 간격을 정확히 맞추기 위해 지역 UTM으로 투영 후 보간한다.
    polygon이 주어지면 폴리곤 밖 좌표는 제외한다.
    반환 좌표는 반올림 기반으로 중복 제거된다.
    """
    if not lines:
        return []

    ref = lines[0].coords[0]  # (lon, lat)
    proj = LocalProjector(ref[0], ref[1])

    seen: set[tuple[int, int]] = set()
    points: list[tuple[float, float]] = []

    for line in lines:
        line_m = shp_transform(lambda xs, ys, z=None: proj.to_m(xs, ys), line)
        length = line_m.length
        if length == 0:
            continue
        n = max(1, int(length // interval_m))
        for i in range(n + 1):
            dist = min(i * interval_m, length)
            p = line_m.interpolate(dist)
            lon, lat = proj.to_deg(p.x, p.y)
            if polygon is not None and not polygon.covers(Point(lon, lat)):
                continue
            key = (round(lat, 5), round(lon, 5))  # 약 1m 격자로 중복 제거
            key_i = (int(key[0] * 1e5), int(key[1] * 1e5))
            if key_i in seen:
                continue
            seen.add(key_i)
            points.append((lat, lon))

    return points


def build_area(config: Config) -> tuple[Polygon, list[LineString], list[tuple[float, float]]]:
    """경계·도로·샘플좌표를 한 번에 준비."""
    polygon = get_boundary_polygon(config)
    lines = get_road_lines(polygon, config)
    points = sample_points_along_lines(lines, config.sample_interval_m, polygon)
    logger.info("샘플 좌표: %d개 (간격 %.0fm)", len(points), config.sample_interval_m)
    return polygon, lines, points
