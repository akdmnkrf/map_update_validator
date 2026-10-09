# Public Overpass mirrors (tried in order).
# Public instances rate-limit heavily (HTTP 429); client retries with backoff.
OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

# Backward compatibility for older deployments / imports.
OVERPASS_URL = OVERPASS_ENDPOINTS[0]

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

OVERPASS_TIMEOUT_SEC = 180
OSRM_TIMEOUT_SEC = 10
OSRM_MAX_WORKERS = 8

# Retry policy for busy public Overpass servers
OVERPASS_MAX_RETRIES = 3
OVERPASS_RETRY_BACKOFF_SEC = 2.0

USER_AGENT = "MapUpdateValidator/2.2.3 (https://github.com/akdmnkrf/map_update_validator)"
