ImpactLabel = str  # "positive" | "negative" | "neutral"


def eta_proxy_change(tags: dict, distance_m: float) -> tuple[float, ImpactLabel]:
    """
    Estimate directional ETA impact from OSM tags (heuristic proxy, not real routing).

    Returns (delta_km, impact) where impact is positive, negative, or neutral.
    """
    if "maxspeed" in tags:
        previous_m = distance_m * 1.10
        impact: ImpactLabel = "positive"
    elif "oneway" in tags:
        previous_m = distance_m * 0.95
        impact = "negative"
    elif "access" in tags:
        previous_m = distance_m * 0.90
        impact = "negative"
    else:
        previous_m = distance_m
        impact = "neutral"

    delta_km = (distance_m - previous_m) / 1000.0
    return round(delta_km, 3), impact
