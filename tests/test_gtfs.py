"""GTFS reader. Every file here is a labeled fixture. No network and no live feed."""
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from server.data.gtfs import TransitFeedError, TransitSchedule, _Freq, _Service, _Stop, _Visit, load_gtfs

PT = ZoneInfo("America/Los_Angeles")
EIGHT_PM = datetime(2026, 10, 24, 20, 0, tzinfo=PT)
ONE_AM = datetime(2026, 10, 25, 1, 0, tzinfo=PT)
FIXTURE = Path(__file__).parent / "fixtures" / "gtfs_demo"


def write_feed(folder: Path, stop_times: str, frequencies: str = "", calendar_dates: str = "",
               calendar: str | None = None) -> None:
    (folder / "stops.txt").write_text(
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "s,Test stop,37.8000,-122.4500\n"
        "mapped,Mapped only,37.8001,-122.4501\n", encoding="utf-8")
    (folder / "trips.txt").write_text(
        "route_id,service_id,trip_id\nbus,wk,t1\n", encoding="utf-8")
    (folder / "stop_times.txt").write_text(stop_times, encoding="utf-8")
    if calendar is None:
        calendar = ("service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
                    "wk,1,1,1,1,1,1,1,20260101,20261231\n")
    (folder / "calendar.txt").write_text(calendar, encoding="utf-8")
    if calendar_dates:
        (folder / "calendar_dates.txt").write_text(calendar_dates, encoding="utf-8")
    if frequencies:
        (folder / "frequencies.txt").write_text(frequencies, encoding="utf-8")


class FixtureFeedTests(unittest.TestCase):
    def test_evening_departure_counts_and_a_mapped_stop_does_not(self):
        schedule = load_gtfs(FIXTURE)
        names = [stop.name for stop in schedule.active_stops(EIGHT_PM, 15)]
        self.assertEqual(names, ["Montgomery BART"])
        self.assertEqual(schedule.active_stops(ONE_AM, 15), [])

    def test_zip_feed_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            zpath = Path(tmp) / "feed.zip"
            with zipfile.ZipFile(zpath, "w") as archive:
                for name in ("stops.txt", "trips.txt", "stop_times.txt", "calendar.txt"):
                    archive.write(FIXTURE / name, name)
            self.assertEqual(len(load_gtfs(zpath).active_stops(EIGHT_PM, 15)), 1)

    def test_missing_folder_names_only_the_folder(self):
        with self.assertRaises(TransitFeedError) as caught:
            load_gtfs(Path("/tmp/does-not-exist-gtfs-demo"))
        self.assertIn("does-not-exist-gtfs-demo", str(caught.exception))
        self.assertNotIn("/tmp", str(caught.exception))


class ScheduleRuleTests(unittest.TestCase):
    def test_time_after_midnight_belongs_to_the_previous_service_day(self):
        days = [False] * 7
        days[5] = True  # Saturday
        stop = _Stop("s", "Night bus", 37.8, -122.45)
        visit = _Visit("s", "sat", 25 * 60)
        service = _Service(days=tuple(days), start="20260101", end="20261231")
        schedule = TransitSchedule({"s": stop}, [visit], {"sat": service}, [])
        self.assertEqual(len(schedule.active_stops(ONE_AM, 15)), 1)
        self.assertEqual(schedule.active_stops(EIGHT_PM, 15), [])

    def test_removed_calendar_date_is_not_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_feed(folder, "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                       "t1,20:05:00,20:05:00,s,1\n",
                       calendar_dates="service_id,date,exception_type\nwk,20261024,2\n")
            schedule = load_gtfs(folder)
            self.assertEqual(schedule.active_stops(EIGHT_PM, 15), [])

    def test_added_date_runs_even_when_the_weekday_is_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_feed(
                folder,
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt1,20:05:00,20:05:00,s,1\n",
                calendar=("service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
                          "start_date,end_date\nwk,0,0,0,0,0,0,0,20260101,20261231\n"),
                calendar_dates="service_id,date,exception_type\nwk,20261024,1\n")
            self.assertEqual(len(load_gtfs(folder).active_stops(EIGHT_PM, 15)), 1)

    def test_frequency_uses_headway_and_the_stop_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_feed(
                folder,
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                "t1,00:00:00,00:00:00,s,1\n"
                "t1,00:10:00,00:10:00,mapped,2\n",
                frequencies="trip_id,start_time,end_time,headway_secs\nt1,18:00:00,22:00:00,3600\n")
            schedule = load_gtfs(folder)
            at_2010 = datetime(2026, 10, 24, 20, 5, tzinfo=PT)
            at_2030 = datetime(2026, 10, 24, 20, 30, tzinfo=PT)
            self.assertEqual([s.name for s in schedule.active_stops(at_2010, 15)], ["Mapped only"])
            self.assertEqual(schedule.active_stops(at_2030, 15), [])

    def test_direct_frequency_without_a_file_respects_headway(self):
        stop = _Stop("s", "Bus", 37.8, -122.45)
        service = _Service(days=(True,) * 7, start="20260101", end="20261231")
        frequent = _Freq("wk", ("s",), 18 * 60, 23 * 60, headway_min=10)
        sparse = _Freq("wk", ("s",), 18 * 60, 23 * 60, headway_min=60)
        often = TransitSchedule({"s": stop}, [], {"wk": service}, [frequent])
        rare = TransitSchedule({"s": stop}, [], {"wk": service}, [sparse])
        query = datetime(2026, 10, 24, 20, 10, tzinfo=PT)
        self.assertEqual(len(often.active_stops(query, 15)), 1)
        self.assertEqual(rare.active_stops(query, 15), [])


if __name__ == "__main__":
    unittest.main()
