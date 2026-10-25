"""Bright Data normalization tests. NO network. Raw records below are hand-written, sanitized
TEST FIXTURES shaped like vendor data. The real open_hours shape is still unverified."""
import unittest
from datetime import datetime, timezone

from server.data.brightdata import _parse_response_body, _to_float, normalize_category, normalize_record
from server.data.models import BoundingBox
from server.data.opening_hours import OpenStatus, evaluate_open_status

FETCHED = datetime(2026, 10, 24, tzinfo=timezone.utc)

FIXTURE_RECORD = {  # TEST FIXTURE
    "name": "Fixture Cafe", "latitude": 37.75, "longitude": -122.45, "category": "Coffee shop",
    "place_id": "fx-1", "open_hours": {"Saturday": "9AM-5PM"},
    "rating": 4.5, "reviews": [{"text": "x"}], "photos": ["u"], "unexpected": {"nested": [1, 2]},
}


class NormalizeRecordTests(unittest.TestCase):
    def test_valid_record(self):
        p = normalize_record(FIXTURE_RECORD, FETCHED)
        self.assertEqual((p.name, p.lat, p.lng, p.category, p.source, p.place_id),
                         ("Fixture Cafe", 37.75, -122.45, "cafe", "brightdata", "fx-1"))
        self.assertEqual(p.raw_category, "Coffee shop")
        self.assertEqual(p.fetched_at, FETCHED)
        self.assertEqual(p.weekly_hours, {5: [(540, 1020)]})

    def test_extra_vendor_fields_do_not_leak(self):
        p = normalize_record(FIXTURE_RECORD, FETCHED)
        for f in ("rating", "reviews", "photos", "unexpected"):
            self.assertFalse(hasattr(p, f))

    def test_input_not_mutated(self):
        rec = dict(FIXTURE_RECORD)
        normalize_record(rec, FETCHED)
        self.assertEqual(rec, FIXTURE_RECORD)

    def test_missing_or_blank_name(self):
        for name in (None, "", "   ", 5, ["a"]):
            self.assertIsNone(normalize_record({**FIXTURE_RECORD, "name": name}, FETCHED), name)
        rec = {k: v for k, v in FIXTURE_RECORD.items() if k != "name"}
        self.assertIsNone(normalize_record(rec, FETCHED))

    def test_missing_coordinates(self):
        for drop in ("latitude", "longitude"):
            rec = {k: v for k, v in FIXTURE_RECORD.items() if k != drop}
            self.assertIsNone(normalize_record(rec, FETCHED), drop)

    def test_malformed_coordinates(self):
        for bad in ("abc", "", None, [], {}, "12,5"):
            self.assertIsNone(normalize_record({**FIXTURE_RECORD, "latitude": bad}, FETCHED), bad)
            self.assertIsNone(normalize_record({**FIXTURE_RECORD, "longitude": bad}, FETCHED), bad)

    def test_non_finite_coordinates_rejected(self):  # regression: used to produce lat=nan
        for bad in ("nan", "NaN", "inf", "-inf", float("nan"), float("inf"), float("-inf")):
            self.assertIsNone(normalize_record({**FIXTURE_RECORD, "latitude": bad}, FETCHED), bad)
            self.assertIsNone(normalize_record({**FIXTURE_RECORD, "longitude": bad}, FETCHED), bad)

    def test_string_and_int_coordinates_converted(self):
        p = normalize_record({**FIXTURE_RECORD, "latitude": "37.8", "longitude": -122}, FETCHED)
        self.assertEqual((p.lat, p.lng), (37.8, -122.0))
        self.assertIsInstance(p.lng, float)

    def test_zero_coordinate_is_kept(self):
        p = normalize_record({**FIXTURE_RECORD, "latitude": 0, "longitude": 0}, FETCHED)
        self.assertEqual((p.lat, p.lng), (0.0, 0.0))

    def test_name_is_stripped(self):
        self.assertEqual(normalize_record({**FIXTURE_RECORD, "name": "  A B  "}, FETCHED).name, "A B")

    def test_error_record_and_non_dict_skipped(self):
        self.assertIsNone(normalize_record({**FIXTURE_RECORD, "error": "crawl failed"}, FETCHED))
        for junk in (None, "str", 3, [], [FIXTURE_RECORD]):
            self.assertIsNone(normalize_record(junk, FETCHED), junk)

    def test_empty_error_field_does_not_block(self):
        self.assertIsNotNone(normalize_record({**FIXTURE_RECORD, "error": None}, FETCHED))

    def test_missing_category_gives_other(self):
        rec = {k: v for k, v in FIXTURE_RECORD.items() if k != "category"}
        p = normalize_record(rec, FETCHED)
        self.assertEqual((p.category, p.raw_category), ("other", None))

    def test_unknown_category_keeps_raw_text(self):
        p = normalize_record({**FIXTURE_RECORD, "category": "Art museum"}, FETCHED)
        self.assertEqual((p.category, p.raw_category), ("other", "Art museum"))

    def test_non_string_category(self):
        p = normalize_record({**FIXTURE_RECORD, "category": ["Cafe"]}, FETCHED)
        self.assertEqual((p.category, p.raw_category), ("other", None))

    def test_missing_hours_is_unknown(self):
        rec = {k: v for k, v in FIXTURE_RECORD.items() if k != "open_hours"}
        p = normalize_record(rec, FETCHED)
        self.assertIsNone(p.weekly_hours)
        self.assertIsNone(p.is_24h)
        t = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
        self.assertEqual(evaluate_open_status(p, t), OpenStatus.UNKNOWN)

    def test_malformed_hours_do_not_drop_the_place(self):
        for bad in ("closed forever", 7, {"Saturday": "???"}, [None], {"Funday": "9AM-5PM"}):
            p = normalize_record({**FIXTURE_RECORD, "open_hours": bad}, FETCHED)
            self.assertIsNotNone(p, bad)
            self.assertIsNone(p.weekly_hours, bad)

    def test_all_days_24h_sets_flag(self):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        p = normalize_record({**FIXTURE_RECORD, "open_hours": {d: "Open 24 hours" for d in days}}, FETCHED)
        self.assertTrue(p.is_24h)

    def test_place_id_variants(self):
        self.assertEqual(normalize_record({**FIXTURE_RECORD, "place_id": 123}, FETCHED).place_id, "123")
        rec = {k: v for k, v in FIXTURE_RECORD.items() if k != "place_id"}
        self.assertIsNone(normalize_record(rec, FETCHED).place_id)


class CategoryTests(unittest.TestCase):
    def test_each_normalized_category(self):
        cases = {"Restaurant": "restaurant", "Pizza place": "restaurant", "Coffee shop": "cafe",
                 "Bakery": "cafe", "Cafe": "cafe", "Café": "cafe", "Cocktail bar": "bar", "Pub": "bar",
                 "Convenience store": "convenience_store", "Supermarket": "convenience_store",
                 "Pharmacy": "pharmacy", "Gas station": "gas_station"}
        for raw, want in cases.items():
            self.assertEqual(normalize_category(raw), want, raw)

    def test_case_whitespace_and_plural(self):
        self.assertEqual(normalize_category("  COFFEE shop "), "cafe")
        self.assertEqual(normalize_category("Pharmacies"), "other")  # plural rule is "s" only
        self.assertEqual(normalize_category("Restaurants"), "restaurant")

    def test_whole_word_matching(self):
        for raw in ("Barber shop", "Steakhouse", "Barbershop", "Cambridge"):
            self.assertEqual(normalize_category(raw), "other", raw)

    def test_first_match_wins(self):
        self.assertEqual(normalize_category("Restaurant and bar"), "restaurant")

    def test_empty_and_wrong_types(self):
        for raw in (None, "", "   ", 5, [], {}):
            self.assertEqual(normalize_category(raw), "other", raw)


class ToFloatAndBodyTests(unittest.TestCase):
    def test_to_float(self):
        self.assertEqual(_to_float("1.5"), 1.5)
        self.assertIsNone(_to_float("x"))
        self.assertIsNone(_to_float(None))
        self.assertIsNone(_to_float("nan"))

    def test_body_formats(self):
        self.assertEqual(_parse_response_body('[{"a":1},{"b":2}]'), [{"a": 1}, {"b": 2}])
        self.assertEqual(_parse_response_body('{"a":1}'), [{"a": 1}])
        self.assertEqual(_parse_response_body('{"a":1}\n\n{"b":2}\n'), [{"a": 1}, {"b": 2}])
        self.assertEqual(_parse_response_body("  \n "), [])

    def test_body_invalid_json_raises(self):
        for text in ("not json", '{"a":1}\n{broken'):
            with self.assertRaises(ValueError):
                _parse_response_body(text)

    def test_body_with_non_dict_items_passes_through(self):
        self.assertEqual(_parse_response_body('[1, "a", null]'), [1, "a", None])  # filtered later


class BoundingBoxFilterOnRecordsTests(unittest.TestCase):
    def test_record_outside_box_is_still_a_valid_place(self):
        # normalize_record does not filter by area; get_places does (see provider tests).
        box = BoundingBox(37.70, -122.50, 37.80, -122.40)
        p = normalize_record({**FIXTURE_RECORD, "latitude": 40.0, "longitude": -120.0}, FETCHED)
        self.assertIsNotNone(p)
        self.assertFalse(box.contains(p.lat, p.lng))


if __name__ == "__main__":
    unittest.main()
