// Time helpers for the demo area (San Francisco). Everything the user types or picks is
// interpreted in America/Los_Angeles so "8 PM" means 8 PM in the city being walked.
import { TIME_ZONE } from "./format";

type Parts = { year: number; month: number; day: number; hour: number; minute: number };

function partsIn(date: Date, timeZone: string): Parts {
  const f = new Intl.DateTimeFormat("en-US", {
    timeZone, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric",
    hour: "numeric", minute: "numeric",
  });
  const get = (type: string) => Number(f.formatToParts(date).find((p) => p.type === type)?.value);
  return { year: get("year"), month: get("month"), day: get("day"), hour: get("hour"), minute: get("minute") };
}

/** The instant when the wall clock in `timeZone` shows the given date and time. */
export function zonedDate(
  year: number, month: number, day: number, hour: number, minute = 0, timeZone: string = TIME_ZONE,
): Date {
  const guess = Date.UTC(year, month - 1, day, hour, minute);
  let result = guess;
  for (let i = 0; i < 2; i++) {
    const p = partsIn(new Date(result), timeZone);
    const shown = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
    result += guess - shown;
  }
  return new Date(result);
}

/** "Tonight" runs until 5 AM: at 1 AM it is still tonight. Returns the 8 PM and 1 AM instants. */
export function tonightTimes(now: Date, timeZone: string = TIME_ZONE): { eightPm: Date; oneAm: Date } {
  const p = partsIn(now, timeZone);
  const base = new Date(Date.UTC(p.year, p.month - 1, p.day));
  if (p.hour < 5) base.setUTCDate(base.getUTCDate() - 1);
  const y = base.getUTCFullYear(), m = base.getUTCMonth() + 1, d = base.getUTCDate();
  const next = new Date(base);
  next.setUTCDate(next.getUTCDate() + 1);
  return {
    eightPm: zonedDate(y, m, d, 20, 0, timeZone),
    oneAm: zonedDate(next.getUTCFullYear(), next.getUTCMonth() + 1, next.getUTCDate(), 1, 0, timeZone),
  };
}

/** Value for <input type="datetime-local"> showing `date` on the Los Angeles clock. */
export function toLocalInput(date: Date, timeZone: string = TIME_ZONE): string {
  const p = partsIn(date, timeZone);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${p.year}-${pad(p.month)}-${pad(p.day)}T${pad(p.hour)}:${pad(p.minute)}`;
}

/** Inverse of toLocalInput: parse the field value as a Los Angeles wall-clock time. */
export function fromLocalInput(value: string, timeZone: string = TIME_ZONE): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!m) return null;
  return zonedDate(Number(m[1]), Number(m[2]), Number(m[3]), Number(m[4]), Number(m[5]), timeZone);
}

export function hourIn(date: Date, timeZone: string = TIME_ZONE): number {
  return partsIn(date, timeZone).hour;
}
