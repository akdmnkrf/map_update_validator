from dataclasses import dataclass, field


@dataclass(frozen=True)
class MapPoint:
    lat: float
    lon: float


@dataclass
class CityAnalysisResult:
    city: str
    changed_ways: int
    total_km: float
    avg_delta_km: float
    maxspeed_changes: int
    oneway_changes: int
    access_changes: int
    eta_positive_ratio_pct: float
    eta_negative_ratio_pct: float
    eta_net_impact_score_pp: float
    critical_changes: int
    critical_ratio_pct: float
    map_points: list[MapPoint] = field(default_factory=list)

    def to_row(self) -> dict:
        return {
            "city": self.city,
            "changed_ways": self.changed_ways,
            "total_km": self.total_km,
            "Δdistance_km": self.avg_delta_km,
            "maxspeed_changes": self.maxspeed_changes,
            "oneway_changes": self.oneway_changes,
            "access_changes": self.access_changes,
            "eta_positive_ratio (%)": self.eta_positive_ratio_pct,
            "eta_negative_ratio (%)": self.eta_negative_ratio_pct,
            "eta_net_impact_score (pp)": self.eta_net_impact_score_pp,
            "critical_changes": self.critical_changes,
            "critical_ratio (%)": self.critical_ratio_pct,
        }
