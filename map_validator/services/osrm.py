from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from map_validator.config import OSRM_MAX_WORKERS, OSRM_TIMEOUT_SEC, OSRM_URL


class OsrmClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    def driving_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}?overview=false"
        response = self._session.get(url, timeout=OSRM_TIMEOUT_SEC)
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes") or []
        return float(routes[0]["distance"]) if routes else 0.0

    def driving_distances_batch(
        self,
        endpoints: list[tuple[float, float, float, float]],
        max_workers: int = OSRM_MAX_WORKERS,
    ) -> list[float]:
        if not endpoints:
            return []

        results: list[float | None] = [None] * len(endpoints)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self._safe_distance, lat1, lon1, lat2, lon2): idx
                for idx, (lat1, lon1, lat2, lon2) in enumerate(endpoints)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                results[idx] = future.result()

        return [value if value is not None else 0.0 for value in results]

    def _safe_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        try:
            return self.driving_distance_m(lat1, lon1, lat2, lon2)
        except (requests.RequestException, KeyError, IndexError, ValueError):
            return 0.0
