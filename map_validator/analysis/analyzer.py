from __future__ import annotations

import datetime as dt
from typing import Any

from map_validator.analysis.eta import eta_proxy_change
from map_validator.constants import TRACKED_TAGS
from map_validator.models import CityAnalysisResult, MapPoint
from map_validator.services.osrm import OsrmClient
from map_validator.services.overpass import OverpassClient, build_overpass_query


def _parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _way_in_date_range(way: dict[str, Any], start: dt.date, end: dt.date) -> bool:
    timestamp = way.get("timestamp")
    if not timestamp:
        return True
    changed = _parse_timestamp(timestamp).date()
    return start <= changed <= end


def _way_endpoints(way: dict[str, Any]) -> tuple[float, float, float, float] | None:
    geometry = way.get("geometry") or []
    if len(geometry) < 2:
        return None
    start, end = geometry[0], geometry[-1]
    return start["lat"], start["lon"], end["lat"], end["lon"]


class CityAnalyzer:
    def __init__(
        self,
        overpass: OverpassClient | None = None,
        osrm: OsrmClient | None = None,
    ) -> None:
        self._overpass = overpass or OverpassClient()
        self._osrm = osrm or OsrmClient()

    def analyze(
        self,
        city: str,
        start_date: dt.date,
        end_date: dt.date,
        highway_types: list[str],
        overpass_data: dict[str, Any] | None = None,
    ) -> CityAnalysisResult | None:
        data = overpass_data
        if data is None:
            query = build_overpass_query(city, start_date, highway_types)
            data = self._overpass.fetch(query)
        return self.analyze_overpass_data(city, start_date, end_date, data)

    def analyze_overpass_data(
        self,
        city: str,
        start_date: dt.date,
        end_date: dt.date,
        data: dict[str, Any] | None,
    ) -> CityAnalysisResult | None:
        if not data or "elements" not in data:
            return None

        ways = [
            element
            for element in data["elements"]
            if element.get("type") == "way"
            and "geometry" in element
            and _way_in_date_range(element, start_date, end_date)
        ]

        tag_counts = {tag: 0 for tag in TRACKED_TAGS}
        endpoints: list[tuple[float, float, float, float]] = []
        way_meta: list[tuple[dict, tuple[float, float, float, float]]] = []

        for way in ways:
            tags = way.get("tags", {})
            for tag in TRACKED_TAGS:
                if tag in tags:
                    tag_counts[tag] += 1

            endpoint = _way_endpoints(way)
            if endpoint is None:
                continue
            endpoints.append(endpoint)
            way_meta.append((tags, endpoint))

        distances_m = self._osrm.driving_distances_batch(endpoints)

        deltas_km: list[float] = []
        impacts: list[str] = []
        map_points: list[MapPoint] = []

        for (tags, (lat1, lon1, lat2, lon2)), distance_m in zip(way_meta, distances_m):
            delta_km, impact = eta_proxy_change(tags, distance_m)
            deltas_km.append(delta_km)
            impacts.append(impact)
            map_points.append(MapPoint(lat=lat1, lon=lon1))

        total_ways = len(ways)
        total_km = sum(distances_m) / 1000.0
        avg_delta_km = sum(deltas_km) / len(deltas_km) if deltas_km else 0.0

        pos_cnt = impacts.count("positive")
        neg_cnt = impacts.count("negative")
        pos_ratio = (pos_cnt / total_ways * 100.0) if total_ways else 0.0
        neg_ratio = (neg_cnt / total_ways * 100.0) if total_ways else 0.0
        critical_changes = sum(tag_counts.values())

        return CityAnalysisResult(
            city=city,
            changed_ways=total_ways,
            total_km=round(total_km, 2),
            avg_delta_km=round(avg_delta_km, 3),
            maxspeed_changes=tag_counts["maxspeed"],
            oneway_changes=tag_counts["oneway"],
            access_changes=tag_counts["access"],
            eta_positive_ratio_pct=round(pos_ratio, 2),
            eta_negative_ratio_pct=round(neg_ratio, 2),
            eta_net_impact_score_pp=round(pos_ratio - neg_ratio, 2),
            critical_changes=critical_changes,
            critical_ratio_pct=round((critical_changes / total_ways * 100.0) if total_ways else 0.0, 2),
            map_points=map_points,
        )
