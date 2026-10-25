import { SOURCES, sourceStatuses, STATUS_TEXT } from "@/lib/sources";
import { formatDayClock } from "@/lib/format";
import type { Trip } from "@/lib/trip";

import { AppHeader } from "./AppHeader";
import { CheckIcon, CloseIcon, HourglassIcon } from "./Icons";

type Props = { trip: Trip; onCancel: () => void };

export function CheckingScreen({ trip, onCancel }: Props) {
  const status = sourceStatuses("loading");
  return (
    <div className="screen stack checking-page">
      <AppHeader title="Checking your walk" backHref="/plan" />
      <div className="pulse-route" aria-hidden="true"><span /></div>
      <div className="card tight stack-sm">
        <div className="row"><span className="dot" /> <strong>{trip.from?.name}</strong></div>
        <div className="row"><span className="dot" style={{ background: "var(--accent)" }} /> <strong>{trip.to?.name}</strong></div>
        {trip.departISO ? (
          <p className="small muted">{formatDayClock(trip.departISO)} · up to {trip.settings.maxExtraMinutes} min extra</p>
        ) : null}
      </div>

      <div className="row between">
        <h2>Checking your walk</h2>
        <span className="tag accent"><span className="dot" /> Live</span>
      </div>
      <p className="muted" role="status" aria-live="polite">
        Checking the streets for when you arrive. This can take a minute.
      </p>
      <ul className="checklist" aria-label="What we are checking">
        {SOURCES.map((s) => (
          <li key={s.id}>
            <span className="spinner" aria-hidden="true" />
            <div>
              <strong>{s.title}</strong>
              <p className="small muted">{s.detail}</p>
            </div>
            <span className="status checking">{STATUS_TEXT[status[s.id]]}</span>
          </li>
        ))}
      </ul>
      <p className="caption row">
        <HourglassIcon /> These checks run together, so we cannot show a percentage.
      </p>
      <button type="button" className="btn secondary" onClick={onCancel}><CloseIcon /> Cancel trip check</button>
      <p className="caption center">Your start, destination, and time stay here.</p>
    </div>
  );
}

export function SourcesPanel({ warnings }: { warnings: string[] }) {
  const status = sourceStatuses("success", warnings);
  return (
    <details className="card tight">
      <summary style={{ minHeight: 44, display: "flex", alignItems: "center", fontWeight: 600 }}>What we checked</summary>
      <ul className="checklist" style={{ marginTop: 8 }}>
        {SOURCES.map((s) => (
          <li key={s.id}>
            {status[s.id] === "done" ? <CheckIcon /> : <HourglassIcon />}
            <div>
              <strong>{s.title}</strong>
              <p className="small muted">{s.detail}</p>
            </div>
            <span className={`status ${status[s.id]}`}>{STATUS_TEXT[status[s.id]]}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
