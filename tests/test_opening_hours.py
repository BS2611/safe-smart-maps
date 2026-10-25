"""Opening-hours parser + evaluator tests. All inputs are hand-written TEST FIXTURES.

Reference dates: 2026-10-24 is a Saturday, 2026-10-25 Sunday, 2026-10-26 Monday,
2026-10-19 Monday. California is on PDT (UTC-7) until 2026-11-01, then PST (UTC-8).
"""
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from server.data.models import Place
from server.data.opening_hours import OpenStatus, evaluate_open_status, parse_weekly_hours

LA = ZoneInfo("America/Los_Angeles")
NY = ZoneInfo("America/New_York")
FETCHED = datetime(2026, 10, 24, tzinfo=timezone.utc)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
OPEN, CLOSED, UNKNOWN = OpenStatus.OPEN, OpenStatus.CLOSED, OpenStatus.UNKNOWN


def place(hours, is_24h=None):
    weekly, derived = parse_weekly_hours(hours)
    return Place("Test", 37.8, -122.4, "cafe", "fixture", FETCHED, weekly, is_24h or derived)


def every_day(text):
    return {d: text for d in DAYS}


def la(month, day, hh, mm=0):
    return datetime(2026, month, day, hh, mm, tzinfo=LA)


class ParseTests(unittest.TestCase):
    def test_minutes_from_midnight(self):
        weekly, _ = parse_weekly_hours({"Monday": "9AM-5PM"})
        self.assertEqual(weekly, {0: [(540, 1020)]})

    def test_12_am_and_12_pm(self):
        weekly, _ = parse_weekly_hours({"Monday": "12 PM-11:59 PM", "Tuesday": "12 AM-6 AM"})
        self.assertEqual(weekly[0], [(720, 1439)])
        self.assertEqual(weekly[1], [(0, 360)])

    def test_overnight_end_exceeds_1440(self):
        weekly, _ = parse_weekly_hours({"Friday": "6 PM-2 AM"})
        self.assertEqual(weekly, {4: [(1080, 1560)]})

    def test_multiple_intervals_per_day(self):
        weekly, _ = parse_weekly_hours({"Monday": "11:30 AM-2 PM, 5 PM-10 PM"})
        self.assertEqual(weekly[0], [(690, 840), (1020, 1320)])

    def test_list_of_strings_per_day(self):
        weekly, _ = parse_weekly_hours({"Monday": ["9AM-12PM", "1PM-5PM"]})
        self.assertEqual(weekly[0], [(540, 720), (780, 1020)])

    def test_dash_variants_and_dotted_ampm(self):
        for text in ("9AM-5PM", "9 AM – 5 PM", "9 AM — 5 PM", "9 a.m.-5 p.m."):
            weekly, _ = parse_weekly_hours({"Monday": text})
            self.assertEqual(weekly, {0: [(540, 1020)]}, text)

    def test_day_name_forms(self):
        for key in ("Monday", "monday", "MON", " mon "):
            weekly, _ = parse_weekly_hours({key: "9AM-5PM"})
            self.assertEqual(list(weekly), [0], key)

    def test_unknown_day_key_ignored(self):
        self.assertEqual(parse_weekly_hours({"Holiday": "9AM-5PM"}), (None, None))

    def test_closed_is_empty_list(self):
        weekly, _ = parse_weekly_hours({"Monday": "Closed", "Tuesday": " closed "})
        self.assertEqual(weekly, {0: [], 1: []})

    def test_invalid_clock_values_make_day_unreadable(self):
        for text in ("13PM-5PM", "0AM-5PM", "9:75AM-5PM"):
            self.assertEqual(parse_weekly_hours({"Monday": text}), (None, None), text)

    def test_garbage_inputs_give_none(self):
        for raw in (None, "Mon 9-5", 42, [], {}, [1, 2], [{"nope": 1}], {"Monday": None},
                    {"Monday": 5}, {5: "9AM-5PM"}, {"Monday": "soon"}):
            self.assertEqual(parse_weekly_hours(raw), (None, None), repr(raw))

    def test_list_shape_keys(self):
        for key in ("hours", "time", "open_hours"):
            weekly, _ = parse_weekly_hours([{"day": "Saturday", key: "10AM-4PM"}])
            self.assertEqual(weekly, {5: [(600, 960)]}, key)

    def test_one_bad_day_does_not_drop_good_days(self):
        weekly, _ = parse_weekly_hours({"Monday": "9AM-5PM", "Tuesday": "garbage"})
        self.assertEqual(weekly, {0: [(540, 1020)]})

    def test_is_24h_requires_all_seven_days(self):
        _, all7 = parse_weekly_hours(every_day("Open 24 hours"))
        self.assertTrue(all7)
        _, six = parse_weekly_hours({d: "Open 24 hours" for d in DAYS[:6]})
        self.assertIsNone(six)
        _, mixed = parse_weekly_hours({**every_day("Open 24 hours"), "Sunday": "9AM-5PM"})
        self.assertIsNone(mixed)

    def test_24h_text_variants(self):
        for text in ("Open 24 hours", "open 24 hour", "24 hours"):
            weekly, _ = parse_weekly_hours({"Monday": text})
            self.assertEqual(weekly, {0: [(0, 1440)]}, text)


class EvaluateTests(unittest.TestCase):
    nine_to_five = staticmethod(lambda: place(every_day("9 AM-5 PM")))

    def test_open_during_hours(self):
        self.assertEqual(evaluate_open_status(self.nine_to_five(), la(10, 24, 12)), OPEN)

    def test_closed_before_opening(self):
        self.assertEqual(evaluate_open_status(self.nine_to_five(), la(10, 24, 8, 59)), CLOSED)

    def test_closed_after_closing(self):
        self.assertEqual(evaluate_open_status(self.nine_to_five(), la(10, 24, 20)), CLOSED)

    def test_exact_opening_minute_is_open(self):
        self.assertEqual(evaluate_open_status(self.nine_to_five(), la(10, 24, 9, 0)), OPEN)

    def test_last_open_minute_and_exact_close(self):
        p = self.nine_to_five()
        self.assertEqual(evaluate_open_status(p, la(10, 24, 16, 59)), OPEN)
        self.assertEqual(evaluate_open_status(p, la(10, 24, 17, 0)), CLOSED)  # close is exclusive

    def test_seconds_do_not_change_the_minute(self):
        p = self.nine_to_five()
        t = datetime(2026, 10, 24, 16, 59, 59, tzinfo=LA)
        self.assertEqual(evaluate_open_status(p, t), OPEN)

    def test_explicit_closed_day(self):
        p = place({**every_day("9AM-5PM"), "Saturday": "Closed"})
        self.assertEqual(evaluate_open_status(p, la(10, 24, 12)), CLOSED)

    def test_missing_hours_unknown(self):
        self.assertEqual(evaluate_open_status(place(None), la(10, 24, 12)), UNKNOWN)

    def test_malformed_hours_unknown(self):
        self.assertEqual(evaluate_open_status(place({"Saturday": "???"}), la(10, 24, 12)), UNKNOWN)

    def test_empty_weekly_hours_dict_is_unknown(self):
        p = Place("T", 1, 1, "cafe", "fixture", FETCHED, {}, None)
        self.assertEqual(evaluate_open_status(p, la(10, 24, 12)), UNKNOWN)

    def test_day_not_listed_is_unknown(self):
        p = place({"Monday": "9AM-5PM"})
        self.assertEqual(evaluate_open_status(p, la(10, 24, 12)), UNKNOWN)  # Saturday missing

    def test_24h_flag_wins(self):
        p = place(every_day("Open 24 hours"))
        for t in (la(10, 24, 0, 0), la(10, 24, 3, 33), la(10, 24, 23, 59)):
            self.assertEqual(evaluate_open_status(p, t), OPEN)

    def test_is_24h_flag_without_weekly_hours(self):
        p = Place("T", 1, 1, "cafe", "fixture", FETCHED, None, True)
        self.assertEqual(evaluate_open_status(p, la(10, 24, 3)), OPEN)

    def test_24h_single_day_covers_that_day_only(self):
        p = place({"Saturday": "Open 24 hours", "Sunday": "9AM-5PM"})
        self.assertEqual(evaluate_open_status(p, la(10, 24, 23, 59)), OPEN)
        self.assertEqual(evaluate_open_status(p, la(10, 25, 3)), CLOSED)

    # ---- overnight ----
    def test_overnight_before_midnight(self):
        p = place(every_day("6 PM-2 AM"))
        self.assertEqual(evaluate_open_status(p, la(10, 24, 17, 59)), CLOSED)
        self.assertEqual(evaluate_open_status(p, la(10, 24, 18, 0)), OPEN)
        self.assertEqual(evaluate_open_status(p, la(10, 24, 23, 59)), OPEN)

    def test_overnight_after_midnight_spillover(self):
        p = place(every_day("6 PM-2 AM"))
        self.assertEqual(evaluate_open_status(p, la(10, 25, 0, 0)), OPEN)
        self.assertEqual(evaluate_open_status(p, la(10, 25, 1, 59)), OPEN)
        self.assertEqual(evaluate_open_status(p, la(10, 25, 2, 0)), CLOSED)  # exact end

    def test_spillover_uses_previous_day_only(self):
        # Only Friday is overnight. Saturday 1 AM is open (Friday spill); Sunday 1 AM is not.
        p = place({**every_day("9AM-5PM"), "Friday": "6 PM-2 AM"})
        self.assertEqual(evaluate_open_status(p, la(10, 24, 1)), OPEN)
        self.assertEqual(evaluate_open_status(p, la(10, 25, 1)), CLOSED)

    def test_spillover_when_today_is_closed(self):
        p = place({**every_day("Closed"), "Friday": "6 PM-2 AM"})
        self.assertEqual(evaluate_open_status(p, la(10, 24, 1)), OPEN)
        self.assertEqual(evaluate_open_status(p, la(10, 24, 3)), CLOSED)

    def test_sunday_to_monday_spillover(self):
        p = place({**every_day("9AM-5PM"), "Sunday": "6 PM-2 AM"})
        self.assertEqual(evaluate_open_status(p, la(10, 26, 1)), OPEN)   # Monday 1 AM
        self.assertEqual(evaluate_open_status(p, la(10, 26, 3)), CLOSED)

    def test_sunday_to_monday_regular_transition(self):
        p = place({**every_day("9AM-5PM"), "Sunday": "Closed"})
        self.assertEqual(evaluate_open_status(p, la(10, 25, 12)), CLOSED)  # Sunday noon
        self.assertEqual(evaluate_open_status(p, la(10, 26, 12)), OPEN)    # Monday noon

    def test_midnight_boundary_between_days(self):
        p = place({"Saturday": "9AM-5PM", "Sunday": "Closed", "Friday": "Closed"})
        self.assertEqual(evaluate_open_status(p, la(10, 24, 23, 59)), CLOSED)
        self.assertEqual(evaluate_open_status(p, la(10, 25, 0, 0)), CLOSED)

    def test_overnight_with_missing_previous_day_is_unknown(self):
        p = place({"Saturday": "9AM-5PM"})
        self.assertEqual(evaluate_open_status(p, la(10, 24, 7)), UNKNOWN)

    def test_multiple_intervals_in_a_day(self):
        p = place(every_day("11:30 AM-2 PM, 5 PM-10 PM"))
        cases = [(11, 29, CLOSED), (11, 30, OPEN), (13, 59, OPEN), (14, 0, CLOSED),
                 (16, 59, CLOSED), (17, 0, OPEN), (21, 59, OPEN), (22, 0, CLOSED)]
        for h, m, want in cases:
            self.assertEqual(evaluate_open_status(p, la(10, 24, h, m)), want, (h, m))

    # ---- time zones ----
    def test_utc_input_converted_to_la(self):
        p = self.nine_to_five()
        self.assertEqual(evaluate_open_status(p, datetime(2026, 10, 24, 19, 0, tzinfo=timezone.utc)), OPEN)    # 12:00 PDT
        self.assertEqual(evaluate_open_status(p, datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)), CLOSED)  # 17:30 PDT

    def test_utc_date_differs_from_la_date(self):
        # 2026-10-25 02:00 UTC is still Saturday 7 PM in LA, so Saturday's hours apply.
        p = place({**every_day("Closed"), "Saturday": "6 PM-9 PM", "Sunday": "Closed"})
        self.assertEqual(evaluate_open_status(p, datetime(2026, 10, 25, 2, 0, tzinfo=timezone.utc)), OPEN)

    def test_new_york_input_converted(self):
        p = self.nine_to_five()
        self.assertEqual(evaluate_open_status(p, datetime(2026, 10, 24, 14, 0, tzinfo=NY)), OPEN)    # 11:00 PDT
        self.assertEqual(evaluate_open_status(p, datetime(2026, 10, 24, 11, 0, tzinfo=NY)), CLOSED)  # 08:00 PDT

    def test_dst_end_uses_correct_offset(self):
        # DST ends 2026-11-01 (Sunday) at 2 AM. 17:00 UTC on Nov 1 is 09:00 PST -> exactly open.
        p = self.nine_to_five()
        self.assertEqual(evaluate_open_status(p, datetime(2026, 11, 1, 17, 0, tzinfo=timezone.utc)), OPEN)
        self.assertEqual(evaluate_open_status(p, datetime(2026, 11, 1, 16, 59, tzinfo=timezone.utc)), CLOSED)

    def test_naive_datetime_rejected(self):
        for p in (self.nine_to_five(), place(None), place(every_day("Open 24 hours"))):
            with self.assertRaises(ValueError):
                evaluate_open_status(p, datetime(2026, 10, 24, 12))


if __name__ == "__main__":
    unittest.main()
