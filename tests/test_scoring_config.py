"""Scoring config loader + startup validation. Temp config files are TEST FIXTURES."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from server.services.scoring_config import CONFIG_PATH, ScoringConfigError, load_scoring_config

EXPECTED_FACTORS = {"open_places", "lighting", "main_road", "help_points", "transit",
                    "activity", "incidents", "turns"}


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.dir = Path(self._dir.name)

    def write(self, obj, name="cfg.json"):
        p = self.dir / name
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
        return p

    def test_real_config_loads(self):
        cfg = load_scoring_config()
        self.assertEqual(cfg["version"], "scoring_v1")
        self.assertEqual(set(cfg["weights"]), EXPECTED_FACTORS)
        self.assertAlmostEqual(sum(cfg["weights"].values()), 1.0)
        self.assertEqual(cfg["segment_length_m"], 50)
        self.assertEqual(cfg["radii_m"]["open_place"], 50)

    def test_default_path_is_repo_scoring_file(self):
        self.assertEqual(CONFIG_PATH.name, "scoring_v1.json")
        self.assertTrue(CONFIG_PATH.is_file())

    def test_sum_exactly_one(self):
        self.assertEqual(load_scoring_config(self.write({"version": "t", "weights": {"a": 0.5, "b": 0.5}}))["version"], "t")

    def test_float_noise_tolerated(self):
        w = {"a": 0.1, "b": 0.2, "c": 0.7}  # sums to 0.9999999999999999 in floats
        load_scoring_config(self.write({"version": "t", "weights": w}))

    def test_sum_above_one_rejected(self):
        with self.assertRaises(ScoringConfigError) as cm:
            load_scoring_config(self.write({"version": "t", "weights": {"a": 0.6, "b": 0.5}}))
        self.assertIn("1.1", str(cm.exception))

    def test_sum_below_one_rejected(self):
        with self.assertRaises(ScoringConfigError):
            load_scoring_config(self.write({"version": "t", "weights": {"a": 0.4, "b": 0.5}}))

    def test_tiny_drift_rejected(self):
        with self.assertRaises(ScoringConfigError):
            load_scoring_config(self.write({"version": "t", "weights": {"a": 0.5, "b": 0.50001}}))

    def test_empty_weights_rejected(self):
        with self.assertRaises(ScoringConfigError):
            load_scoring_config(self.write({"version": "t", "weights": {}}))

    def test_real_config_with_one_weight_bumped_rejected(self):
        cfg = json.loads(CONFIG_PATH.read_text())
        cfg["weights"]["lighting"] += 0.05
        with self.assertRaises(ScoringConfigError):
            load_scoring_config(self.write(cfg))

    # Missing / malformed files: today these raise raw Python errors, not ScoringConfigError.
    # Whether to wrap them is an open question (see agent log). We only prove they fail loudly.
    LOUD = (OSError, ValueError, KeyError, TypeError, ScoringConfigError)

    def test_missing_file_fails_loudly(self):
        with self.assertRaises(self.LOUD):
            load_scoring_config(self.dir / "nope.json")

    def test_malformed_json_fails_loudly(self):
        for text in ("{not json", "", "[1,2"):
            with self.assertRaises(self.LOUD, msg=text):
                load_scoring_config(self.write(text))

    def test_missing_weights_fails_loudly(self):
        with self.assertRaises(self.LOUD):
            load_scoring_config(self.write({"version": "t"}))

    def test_non_numeric_weight_fails_loudly(self):
        with self.assertRaises(self.LOUD):
            load_scoring_config(self.write({"version": "t", "weights": {"a": "0.5", "b": 0.5}}))

    def test_top_level_not_object_fails_loudly(self):
        with self.assertRaises(self.LOUD):
            load_scoring_config(self.write([1, 2]))


class StartupValidationTests(unittest.TestCase):
    """Uses the FastAPI lifespan, which runs the loader at startup."""

    def test_app_starts_with_real_config_and_stores_it(self):
        from server.main import app
        with TestClient(app) as client:
            self.assertEqual(client.get("/v1/health").status_code, 200)
            self.assertEqual(app.state.scoring_config["version"], "scoring_v1")

    def test_app_refuses_to_start_with_bad_weights(self):
        import server.main as main
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.json"
            bad.write_text(json.dumps({"version": "t", "weights": {"a": 0.9, "b": 0.9}}))
            with mock.patch.object(main, "load_scoring_config", lambda: load_scoring_config(bad)):
                with self.assertRaises(ScoringConfigError):
                    with TestClient(main.app):
                        pass


if __name__ == "__main__":
    unittest.main()
