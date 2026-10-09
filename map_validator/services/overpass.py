from __future__ import annotations

import datetime as dt
import time
from typing import Any

import requests

from map_validator.config import OVERPASS_TIMEOUT_SEC, USER_AGENT

try:
    from map_validator.config import (
        OVERPASS_ENDPOINTS,
        OVERPASS_MAX_RETRIES,
        OVERPASS_RETRY_BACKOFF_SEC,
    )
except ImportError:
    OVERPASS_ENDPOINTS = (
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    )
    OVERPASS_MAX_RETRIES = 3
    OVERPASS_RETRY_BACKOFF_SEC = 2.0

_RETRYABLE_STATUS = {429, 502, 503, 504}


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
        self._session.headers.setdefault("User-Agent", USER_AGENT)

    def fetch(self, query: str) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        errors: list[str] = []

        for endpoint in OVERPASS_ENDPOINTS:
            try:
                return self._fetch_with_retries(endpoint, query, headers)
            except requests.RequestException as exc:
                errors.append(f"{endpoint}: {exc}")

        if any("429" in err for err in errors):
            raise requests.HTTPError(
                "Overpass sunucuları meşgul (HTTP 429 — Too Many Requests). "
                "Bu senin tarih/şehir seçiminden değil; herkese açık Overpass kotası dolmuş. "
                "2–5 dakika bekleyip tekrar dene. "
                + " | ".join(errors)
            )

        raise requests.RequestException(
            "Overpass sunucularına ulaşılamadı. " + " | ".join(errors)
        )

    def _fetch_with_retries(
        self,
        endpoint: str,
        query: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        last_error: requests.RequestException | None = None

        for attempt in range(OVERPASS_MAX_RETRIES):
            try:
                response = self._session.post(
                    endpoint,
                    data=query,
                    headers=headers,
                    timeout=OVERPASS_TIMEOUT_SEC,
                )
                if response.status_code in _RETRYABLE_STATUS and attempt < OVERPASS_MAX_RETRIES - 1:
                    retry_after = response.headers.get("Retry-After")
                    wait_sec = float(retry_after) if retry_after and retry_after.isdigit() else (
                        OVERPASS_RETRY_BACKOFF_SEC * (2**attempt)
                    )
                    time.sleep(min(wait_sec, 30.0))
                    continue

                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt < OVERPASS_MAX_RETRIES - 1:
                    time.sleep(OVERPASS_RETRY_BACKOFF_SEC * (2**attempt))
                    continue
                raise

        assert last_error is not None
        raise last_error
