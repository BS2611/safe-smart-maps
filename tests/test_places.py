"""Tests for hours parsing/evaluation and record normalization.

All data below is a LABELED TEST FIXTURE written by hand. The open_hours shape is an
ASSUMPTION (the Bright Data docs do not show it); verify against a real response.
"""
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from server.data.brightdata import normalize_category, normalize_record, _parse_response_body
from server.data.models import Place
from server.data.opening_hours import OpenStatus, evaluate_open_status, parse_weekly_hours

LA = ZoneInfo("America/Los_Angeles")
FETCHED = datetime(2026, 10, 24, tzinfo=timezone.utc)
# 2026-10-24 is a Saturday.


def place(hours, is_24h=None):
    weekly, derived = parse_weekly_hours(hours)
    return Place("Test", 37.8, -122.4, "cafe", "fixture", FETCHED, weekly, is_24h or derived)


def at(day, hh, mm=0):
    return datetime(2026, 10, day, hh, mm, tzinfo=LA)


ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class HoursTests(unittest.TestCase):
    def test_open_and_closed_inside_day(self):
        p = place({d: "9 AM-5 PM" for d in ALL_DAYS})
        self.assertEqual(evaluate_open_status(p, at(24, 12)), OpenStatus.OPEN)
        self.assertEqual(evaluate_open_status(p, at(24, 20)), OpenStatus.CLOSED)
        self.assertEqual(evaluate_open_status(p, at(24, 17)), OpenStatus.CLOSED)  # close is exclusive

    def test_missing_hours_is_unknown_not_closed(self):
        p = place(None)
        self.assertIsNone(p.weekly_hours)
        self.assertEqual(evaluate_open_status(p, at(24, 12)), OpenStatus.UNKNOWN)

    def test_unreadable_text_is_unknown(self):
        self.assertEqual(parse_weekly_hours({"Saturday": "by appointment"}), (None, None))

    def test_unreadable_day_is_unknown_for_that_day_only(self):
        p = place({"Saturday": "by appointment", "Sunday": "9AM-5PM"})
        self.assertEqual(evaluate_open_status(p, at(24, 12)), OpenStatus.UNKNOWN)

    def test_explicit_closed_day(self):
        p = place({d: ("Closed" if d == "Saturday" else "9AM-5PM") for d in ALL_DAYS})
        self.assertEqual(evaluate_open_status(p, at(24, 12)), OpenStatus.CLOSED)

    def test_24h_every_day(self):
        p = place({d: "Open 24 hours" for d in ALL_DAYS})
        self.assertTrue(p.is_24h)
        self.assertEqual(evaluate_open_status(p, at(25, 3)), OpenStatus.OPEN)

    def test_24h_one_day_only_is_not_is_24h(self):
        p = place({"Saturday": "Open 24 hours", "Sunday": "9AM-5PM"})
        self.assertFalse(p.is_24h)

    def test_past_midnight_hours(self):
        # Saturday 6 PM-2 AM: open Sat 11 PM and Sun 1 AM, closed Sun 3 AM.
        p = place({d: "6 PM-2 AM" for d in ALL_DAYS})
        self.assertEqual(evaluate_open_status(p, at(24, 23)), OpenStatus.OPEN)
        self.assertEqual(evaluate_open_status(p, at(25, 1)), OpenStatus.OPEN)
        self.assertEqual(evaluate_open_status(p, at(25, 3)), OpenStatus.CLOSED)

    def test_split_hours_and_en_dash(self):
        p = place({d: "11:30 AM–2 PM, 5 PM–10 PM" for d in ALL_DAYS})
        self.assertEqual(evaluate_open_status(p, at(24, 15)), OpenStatus.CLOSED)
        self.assertEqual(evaluate_open_status(p, at(24, 19)), OpenStatus.OPEN)

    def test_arrival_in_other_timezone_is_converted(self):
        p = place({d: "9 AM-5 PM" for d in ALL_DAYS})
        utc_noon_pt = datetime(2026, 10, 24, 19, 0, tzinfo=timezone.utc)  # 12:00 PDT
        self.assertEqual(evaluate_open_status(p, utc_noon_pt), OpenStatus.OPEN)

    def test_naive_arrival_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_open_status(place(None), datetime(2026, 10, 24, 12))

    def test_list_shape(self):
        weekly, _ = parse_weekly_hours([{"day": "Saturday", "hours": "10AM-4PM"}])
        self.assertEqual(weekly, {5: [(600, 960)]})


class NormalizeTests(unittest.TestCase):
    def test_category(self):
        self.assertEqual(normalize_category("Coffee shop"), "cafe")
        self.assertEqual(normalize_category(None), "other")
        self.assertEqual(normalize_category("Barber shop"), "other")
        self.assertEqual(normalize_category("Steakhouse"), "other")
        self.assertEqual(normalize_category("Museum"), "other")

    def test_record_ok_and_partial(self):
        rec = {"name": " Cafe X ", "latitude": "37.80", "longitude": -122.44,
               "category": "Cafe", "place_id": "abc"}
        p = normalize_record(rec, FETCHED)
        self.assertEqual((p.name, p.lat, p.category, p.source), ("Cafe X", 37.80, "cafe", "brightdata"))
        self.assertIsNone(p.weekly_hours)

    def test_record_unusable(self):
        self.assertIsNone(normalize_record({"name": "No coords"}, FETCHED))
        self.assertIsNone(normalize_record({"error": "x", "name": "a", "latitude": 1, "longitude": 1}, FETCHED))

    def test_response_body_array_and_ndjson(self):
        self.assertEqual(_parse_response_body('[{"a":1}]'), [{"a": 1}])
        self.assertEqual(_parse_response_body('{"a":1}\n{"b":2}'), [{"a": 1}, {"b": 2}])
        self.assertEqual(_parse_response_body(""), [])


if __name__ == "__main__":
    unittest.main()
