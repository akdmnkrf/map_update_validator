from __future__ import annotations

import datetime as dt
from typing import Any

import requests

from map_validator.config import OVERPASS_TIMEOUT_SEC, OVERPASS_URL


def build_overpass_query(city_name: str, start_dt: dt.date, highway_types: list[str]) -> str:
    hw_regex = "|".join(highway_types)
    start_iso = f"{start_dt.isoformat()}T00:00:00Z"
    return f"""
[out:json][timeout:{OVERPASS_TIMEOUT_SEC}];
area["name"="{city_name}"]->.search_area;
(
  way["highway"~"{hw_regex}"](newer:"{start_iso}")(area.search_area);
);
out geom;
""".strip()


class OverpassClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    def fetch(self, query: str) -> dict[str, Any] | None:
        response = self._session.post(
            OVERPASS_URL,
            data=query,
            timeout=OVERPASS_TIMEOUT_SEC,
        )
        response.raise_for_status()
        return response.json()
