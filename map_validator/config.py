# Public Overpass mirrors (tried in order).
# overpass-api.de often returns HTTP 406 from cloud/datacenter IPs — not used.
OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

# Backward compatibility for older deployments / imports.
OVERPASS_URL = OVERPASS_ENDPOINTS[0]

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

OVERPASS_TIMEOUT_SEC = 180
OSRM_TIMEOUT_SEC = 10
OSRM_MAX_WORKERS = 8

USER_AGENT = "MapUpdateValidator/2.2.2 (https://github.com/akdmnkrf/map_update_validator)"
