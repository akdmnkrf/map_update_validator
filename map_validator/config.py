# Public Overpass mirrors (tried in order).
# Do not use overpass-api.de as primary — it often returns HTTP 406 from cloud hosts.
OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

OVERPASS_TIMEOUT_SEC = 180
OSRM_TIMEOUT_SEC = 10
OSRM_MAX_WORKERS = 8

USER_AGENT = "MapUpdateValidator/2.2.1 (https://github.com/akdmnkrf/map_update_validator)"
