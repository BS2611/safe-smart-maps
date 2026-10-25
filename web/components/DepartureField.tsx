"use client";

import { useMemo, useState } from "react";

import { formatDayClock } from "@/lib/format";
import { fromLocalInput, toLocalInput, tonightTimes } from "@/lib/time";

type Mode = "now" | "eight" | "one" | "pick";

type Props = {
  value: string | null;           // ISO instant, or null = leave now
  onChange: (iso: string | null) => void;
  now?: Date;
};

export function DepartureField({ value, onChange, now }: Props) {
  const base = useMemo(() => now ?? new Date(), [now]);
  const { eightPm, oneAm } = useMemo(() => tonightTimes(base), [base]);
  const initial: Mode = value === null ? "now"
    : value === eightPm.toISOString() ? "eight"
      : value === oneAm.toISOString() ? "one" : "pick";
  const [mode, setMode] = useState<Mode>(initial);

  function choose(next: Mode) {
    setMode(next);
    if (next === "now") onChange(null);
    if (next === "eight") onChange(eightPm.toISOString());
    if (next === "one") onChange(oneAm.toISOString());
    if (next === "pick") onChange(value ?? base.toISOString());
  }

  return (
    <div className="field">
      <span className="label" id="depart-label">Leave</span>
      <div className="chips" role="group" aria-labelledby="depart-label">
        <button type="button" className="chip" aria-pressed={mode === "now"} onClick={() => choose("now")}>Leave now</button>
        <button type="button" className="chip" aria-pressed={mode === "eight"} onClick={() => choose("eight")}>Tonight 8 PM</button>
        <button type="button" className="chip" aria-pressed={mode === "one"} onClick={() => choose("one")}>Tonight 1 AM</button>
        <button type="button" className="chip" aria-pressed={mode === "pick"} onClick={() => choose("pick")}>Pick a time</button>
      </div>
      {mode === "pick" ? (
        <input
          type="datetime-local" className="input" aria-label="Departure time (San Francisco time)"
          style={{ marginTop: 8 }}
          value={toLocalInput(new Date(value ?? base))}
          onChange={(e) => {
            const d = fromLocalInput(e.target.value);
            if (d) onChange(d.toISOString());
          }}
        />
      ) : null}
      <p className="small muted" style={{ marginTop: 8 }}>
        {value ? `${formatDayClock(value)} (San Francisco time). ` : "Now. "}
        Scores use the time you reach each street, not when you leave.
      </p>
    </div>
  );
}
