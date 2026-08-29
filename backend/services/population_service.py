"""
Population-impact lookups.

There is no free, key-less, reliable API for "population density at this
exact lat/lon" -- real ones (WorldPop, national census APIs, Meta's
High Resolution Settlement Layer) need an API key and/or a paid tier. So
this module is honest about what it actually does:

1. REFERENCE DATA: for the three demo disasters this project targets
   (Kathmandu Valley / Nepal floods, Assam / Brahmaputra floods,
   Ahmedabad), a bounding box is checked first. If the given lat/lon
   falls inside one, we return published, real approximate population
   density figures for that region (sourced from public census/UN
   estimates -- not a live feed, and labeled as such).
2. DEMO DATA fallback: anywhere else, a deterministic mock estimate is
   generated from the coordinates (same input -> same output every time),
   clearly labeled so it is never confused with real data.

Swap step 1's lookup for a real geospatial population API later without
changing the function signature.
"""
from typing import Dict, Any
import math

# ---------------------------------------------------------------------------
# Known disaster-region reference data (approximate, public-estimate figures)
# ---------------------------------------------------------------------------
# bounding box: (lat_min, lat_max, lon_min, lon_max)
_REGIONS = [
    {
        "name": "Kathmandu Valley, Nepal",
        "bbox": (27.60, 27.80, 85.20, 85.45),
        "population_density_per_km2": 4400,   # approx, Kathmandu Valley urban core
        "source": "Public census / UN-Habitat estimate for Kathmandu Valley urban area",
    },
    {
        "name": "Guwahati / Assam, India",
        "bbox": (26.05, 26.25, 91.65, 91.85),
        "population_density_per_km2": 2200,   # approx, Guwahati urban area
        "source": "Census of India (Guwahati Municipal Corporation area, approx.)",
    },
    {
        "name": "Ahmedabad, India",
        "bbox": (22.95, 23.15, 72.45, 72.70),
        "population_density_per_km2": 12500,  # approx, Ahmedabad city core
        "source": "Census of India / AMC estimate for Ahmedabad urban core",
    },
]


def _match_region(lat: float, lon: float):
    for region in _REGIONS:
        lat_min, lat_max, lon_min, lon_max = region["bbox"]
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return region
    return None


def get_population_impact(lat: float, lon: float, disaster_radius_km: float = 2.0, area_km2_override: float = None) -> Dict[str, Any]:
    """
    Returns population context for a site. See module docstring for the
    REFERENCE DATA vs DEMO DATA distinction -- always check `data_label`
    before treating a number as real.

    area_km2_override: pass this to use an area derived from actual
    uploaded imagery/video coverage (see upload.py) instead of the
    default fixed-radius circle -- this is what makes the population
    estimate respond to what's actually visible in the photos, not just
    the pin location.
    """
    area_km2 = area_km2_override if area_km2_override is not None else math.pi * disaster_radius_km ** 2
    region = _match_region(lat, lon)

    if region:
        density = region["population_density_per_km2"]
        estimated_affected = round(density * area_km2)
        return {
            "data_label": "REFERENCE DATA (public estimate)",
            "region_matched": region["name"],
            "source": region["source"],
            "estimated_affected_population": estimated_affected,
            "population_density": density,
            "households_affected": estimated_affected // 4,
            "vulnerable_population_pct": 15,
            "area_km2_used": round(area_km2, 3),
            "area_source": "derived from uploaded imagery coverage" if area_km2_override is not None else "fixed default radius",
        }

    # Fallback: deterministic mock so repeated calls for the same point are stable.
    seed = int(abs(lat * 1000) + abs(lon * 1000)) % 50000
    estimated_affected = 500 + seed
    return {
        "data_label": "DEMO DATA (simulated -- no reference data for this location)",
        "region_matched": None,
        "source": None,
        "estimated_affected_population": estimated_affected,
        "population_density": round(estimated_affected / area_km2, 1),
        "households_affected": estimated_affected // 4,
        "vulnerable_population_pct": 15,
        "area_km2_used": round(area_km2, 3),
        "area_source": "derived from uploaded imagery coverage" if area_km2_override is not None else "fixed default radius",
    }
