"""Load the service-owned 2026 table; never depend on another microservice."""
import json
import math
from pathlib import Path

from src.core.exceptions import DuLieuKhongHopLe

CONVERSION_TABLE_PATH = Path(__file__).resolve().parents[1] / "data" / "conversion_scales_2026.json"


def load_conversion_scales() -> dict:
    # Resolve from this module so Docker WORKDIR and the caller CWD do not matter.
    with CONVERSION_TABLE_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def convert_to_thpt(method: str, score: float, year: int = 2026) -> float:
    # The table only defines these three methods and the 2026 admission season.
    if year != 2026 or method not in {"hoc_ba", "hsa", "tsa"}:
        raise DuLieuKhongHopLe("Unsupported conversion method or year")
    if not math.isfinite(score):
        raise DuLieuKhongHopLe("Score must be finite")
    for row in load_conversion_scales()[f"{method}_to_thpt"]:
        lower, upper = row[f"{method}_min"], row[f"{method}_max"]
        if lower <= score <= upper:
            # Linear interpolation within a published interval; no extrapolation.
            ratio = (score - lower) / (upper - lower)
            return row["thpt_min"] + ratio * (row["thpt_max"] - row["thpt_min"])
    raise DuLieuKhongHopLe("Score outside the published conversion intervals")
