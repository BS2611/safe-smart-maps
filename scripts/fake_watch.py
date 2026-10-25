"""Pretend to be the Galaxy Watch, so the phone screen can be tested without the real watch.

Usage (backend running, phone page showing a pairing code):
    python -m scripts.fake_watch --code 123456
    python -m scripts.fake_watch --code 123456 --bpm 80 --spike --prompt --seconds 20
    python -m scripts.fake_watch --code 123456 --source simulated   # readings show as Simulated

Not a real heart rate: by default readings are sent with source "simulated" so the phone labels them.
Use --source wearos only to test how a real watch reading looks on the phone.
"""
import argparse
import time
from datetime import UTC, datetime

import httpx


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default="http://localhost:8000", help="backend URL")
    p.add_argument("--code", required=True, help="6-digit code shown on the phone")
    p.add_argument("--bpm", type=int, default=80, help="starting beats per minute")
    p.add_argument("--seconds", type=int, default=15, help="how long to keep sending")
    p.add_argument("--interval", type=float, default=1.0, help="seconds between readings")
    p.add_argument("--source", choices=["simulated", "wearos", "band"], default="simulated")
    p.add_argument("--spike", action="store_true", help="raise the bpm halfway through")
    p.add_argument("--prompt", action="store_true", help="show the Are you OK? prompt, then send the alert")
    p.add_argument("--ok", action="store_true", help="with --prompt: answer OK instead of sending the alert")
    args = p.parse_args(argv)

    with httpx.Client(base_url=args.base, timeout=10) as http:
        paired = http.post("/v1/watch/pair", json={"pair_code": args.code, "device": "wearos"})
        if paired.status_code != 200:
            print(f"Pairing failed ({paired.status_code}): {paired.json()['error']['message']}")
            return 1
        trip_id = paired.json()["trip_id"]
        auth = {"Authorization": f"Bearer {paired.json()['watch_token']}"}
        print("Paired. Sending readings (fake).")

        steps = max(1, int(args.seconds / args.interval))
        for i in range(steps):
            bpm = args.bpm + (35 if args.spike and i >= steps // 2 else 0) + (i % 3)
            body = {"bpm": bpm, "ts": datetime.now(UTC).isoformat(), "source": args.source}
            r = http.post("/v1/watch/heartbeat", json=body, headers=auth)
            if r.status_code != 204:
                print(f"Reading rejected ({r.status_code})")
                return 1
            print(f"  sent {bpm} bpm")
            time.sleep(args.interval)

        if args.prompt:
            http.post("/v1/watch/prompt", headers=auth)
            print("Prompt shown on the phone.")
            time.sleep(3)
            if args.ok:
                http.post("/v1/alerts/ack", json={"trip_id": trip_id, "ok": True})
                print("Answered: OK.")
            else:
                status = http.post("/v1/alerts", json={"trip_id": trip_id}, headers=auth).json()["status"]
                print(f"Alert recorded: {status} (nothing is really sent).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
