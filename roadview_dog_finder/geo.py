"""좌표계 변환 유틸.

위경도(EPSG:4326)와 지역 UTM(미터 단위) 사이를 변환한다. 미터 단위가 있어야
"20m 간격 샘플링", "도로에서 25m 이내" 같은 거리 계산을 정확히 할 수 있다.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Transformer


def utm_epsg_for(lon: float, lat: float) -> int:
    """주어진 좌표가 속한 UTM 존의 EPSG 코드를 반환."""
    zone = int((lon + 180.0) / 6.0) + 1
    if lat >= 0:
        return 32600 + zone  # 북반구
    return 32700 + zone  # 남반구


@lru_cache(maxsize=32)
def _transformers(epsg: int) -> tuple[Transformer, Transformer]:
    to_m = Transformer.from_crs(4326, epsg, always_xy=True)
    to_deg = Transformer.from_crs(epsg, 4326, always_xy=True)
    return to_m, to_deg


class LocalProjector:
    """한 지역 내에서 (lon,lat)<->(x,y meters)를 변환하는 헬퍼."""

    def __init__(self, ref_lon: float, ref_lat: float):
        self.epsg = utm_epsg_for(ref_lon, ref_lat)
        self._to_m, self._to_deg = _transformers(self.epsg)

    def to_m(self, lon: float, lat: float) -> tuple[float, float]:
        return self._to_m.transform(lon, lat)

    def to_deg(self, x: float, y: float) -> tuple[float, float]:
        lon, lat = self._to_deg.transform(x, y)
        return lon, lat
