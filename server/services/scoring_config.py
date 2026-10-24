"""Loads scoring/scoring_v1.json and checks it. Service layer: no HTTP, no providers."""
import json
import math
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "scoring" / "scoring_v1.json"


class ScoringConfigError(RuntimeError):
    pass


def load_scoring_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
    total = sum(config["weights"].values())
    if not math.isclose(total, 1.0, abs_tol=1e-9):
        raise ScoringConfigError(
            f"{config.get('version')}: weights sum to {total}, expected 1.0"
        )
    return config
