# Overpass mirrors tried in order (first reachable wins).
# overpass-api.de often returns 406 for cloud/datacenter IPs.
OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

OVERPASS_TIMEOUT_SEC = 180
OSRM_TIMEOUT_SEC = 10
OSRM_MAX_WORKERS = 8

USER_AGENT = "MapUpdateValidator/2.2 (https://github.com/akdmnkrf/map_update_validator)"
