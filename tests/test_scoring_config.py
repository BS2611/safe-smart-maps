"""Tests for scoring/scoring_v1.json and its loader (server/services/scoring_config.py)."""
import json

import pytest

from server.services.scoring_config import CONFIG_PATH, ScoringConfigError, load_scoring_config

EXPECTED_WEIGHTS = {
    "open_places": 0.25,
    "lighting": 0.20,
    "main_road": 0.15,
    "help_points": 0.10,
    "transit": 0.10,
    "activity": 0.10,
    "incidents": 0.05,
    "turns": 0.05,
}


def write_config(tmp_path, weights):
    path = tmp_path / "scoring_test.json"
    path.write_text(json.dumps({"version": "scoring_test", "weights": weights}), encoding="utf-8")
    return path


def test_real_config_matches_the_spec_weights():
    config = load_scoring_config()
    assert config["version"] == "scoring_v1"
    assert config["weights"] == pytest.approx(EXPECTED_WEIGHTS)
    assert sum(config["weights"].values()) == pytest.approx(1.0)


def test_real_config_thresholds_match_the_spec():
    config = load_scoring_config()
    assert config["segment_length_m"] == 50
    assert config["radii_m"] == {"open_place": 50, "help_point": 150, "coverage": 75}
    cont = config["continuity"]
    assert cont["coverage_target"] == 0.80
    assert cont["gap_limit_m"] == 150
    assert cont["window_m"] == 200
    assert cont["avg_weight"] + cont["worst_window_weight"] == pytest.approx(1.0)


def test_config_file_is_where_the_contract_says():
    assert CONFIG_PATH.as_posix().endswith("scoring/scoring_v1.json")


def test_weights_not_summing_to_one_are_rejected(tmp_path):
    path = write_config(tmp_path, {"a": 0.5, "b": 0.6})
    with pytest.raises(ScoringConfigError, match="expected 1.0"):
        load_scoring_config(path)


def test_weights_summing_to_one_are_accepted(tmp_path):
    path = write_config(tmp_path, {"a": 0.5, "b": 0.5})
    assert load_scoring_config(path)["version"] == "scoring_test"


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scoring_config(tmp_path / "nope.json")
