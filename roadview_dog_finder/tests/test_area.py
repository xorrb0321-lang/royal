"""좌표 샘플링(순수 기하) 오프라인 테스트.

네트워크(osmnx/streetlevel)나 GPU 없이 실행 가능하다.

  python -m roadview_dog_finder.tests.test_area
  # 또는 pytest
"""

from __future__ import annotations

from shapely.geometry import LineString, box

from roadview_dog_finder.area import sample_points_along_lines
from roadview_dog_finder.geo import LocalProjector


def _meters_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    # a, b = (lat, lon)
    proj = LocalProjector(a[1], a[0])
    ax, ay = proj.to_m(a[1], a[0])
    bx, by = proj.to_m(b[1], b[0])
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def test_sampling_spacing_and_count():
    # 서울 부근 위경도에서 동쪽으로 약간 뻗은 직선
    lon0, lat0 = 127.0, 37.5
    proj = LocalProjector(lon0, lat0)
    x0, y0 = proj.to_m(lon0, lat0)
    # 정확히 200m 동쪽 지점
    lon1, lat1 = proj.to_deg(x0 + 200.0, y0)
    line = LineString([(lon0, lat0), (lon1, lat1)])

    pts = sample_points_along_lines([line], interval_m=20.0)
    # 200m / 20m = 10 구간 -> 대략 11개 지점
    assert 10 <= len(pts) <= 12, f"예상 11개 내외, 실제 {len(pts)}"

    # 연속 지점 간격이 대략 20m인지 확인
    d = _meters_between(pts[0], pts[1])
    assert 18.0 <= d <= 22.0, f"간격 20m 예상, 실제 {d:.1f}m"


def test_polygon_filtering():
    lon0, lat0 = 127.0, 37.5
    proj = LocalProjector(lon0, lat0)
    x0, y0 = proj.to_m(lon0, lat0)
    lon1, lat1 = proj.to_deg(x0 + 300.0, y0)
    line = LineString([(lon0, lat0), (lon1, lat1)])

    # 시작점 부근 ~100m만 덮는 작은 폴리곤
    lon_mid, lat_mid = proj.to_deg(x0 + 100.0, y0)
    poly = box(min(lon0, lon_mid) - 0.001, lat0 - 0.001, max(lon0, lon_mid), lat0 + 0.001)

    all_pts = sample_points_along_lines([line], interval_m=20.0)
    clipped = sample_points_along_lines([line], interval_m=20.0, polygon=poly)
    assert len(clipped) < len(all_pts), "폴리곤 밖 좌표가 제외되어야 함"
    for lat, lon in clipped:
        assert lon <= lon_mid + 1e-6, "샘플이 폴리곤 범위를 벗어남"


def test_empty_input():
    assert sample_points_along_lines([], interval_m=20.0) == []


def _run_all() -> int:
    tests = [
        test_sampling_spacing_and_count,
        test_polygon_filtering,
        test_empty_input,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
