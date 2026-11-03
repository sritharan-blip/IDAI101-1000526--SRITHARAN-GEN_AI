from __future__ import annotations

import math


def estimate_yield(size_ha: float, rainfall_mm: float, fertilizer_investment: float,
                   soil_type: str, crop: str) -> dict[str, float | str]:
    """Produce an explicitly illustrative scenario, not an agronomic forecast."""
    base_tonnes_per_ha = 3.2
    soil_factor = {"Loamy": 1.05, "Silty": 1.0, "Sandy": 0.86, "Clay": 0.9}.get(soil_type, 0.95)
    rainfall_factor = max(0.55, min(1.12, 0.6 + rainfall_mm / 900))
    investment_factor = 1 + 0.18 * (1 - math.exp(-max(fertilizer_investment, 0) / 800))
    yield_per_ha = base_tonnes_per_ha * soil_factor * rainfall_factor * investment_factor
    total_yield = max(size_ha, 0) * yield_per_ha
    return {
        "crop": crop or "Unspecified crop",
        "yield_per_ha": yield_per_ha,
        "total_yield": total_yield,
        "rainfall_factor": rainfall_factor,
        "investment_factor": investment_factor,
    }
