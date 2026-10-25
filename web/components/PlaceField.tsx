"use client";

import { useEffect, useId, useState } from "react";

import { hasGeocoding, searchPlaces } from "@/lib/geocode";
import type { Place } from "@/lib/types";

import { SearchIcon } from "./Icons";

type Props = {
  label: string;
  value: Place | null;
  onChange: (place: Place | null) => void;
  presets: Place[];
  placeholder?: string;
  allowMyLocation?: boolean;
  onLocationDenied?: () => void;
};

export function PlaceField({ label, value, onChange, presets, placeholder, allowMyLocation, onLocationDenied }: Props) {
  const id = useId();
  const [text, setText] = useState(value?.name ?? "");
  const [results, setResults] = useState<Place[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const searchable = hasGeocoding();

  useEffect(() => { setText(value?.name ?? ""); }, [value]);

  useEffect(() => {
    if (!searchable || value || text.trim().length < 3) {
      setResults([]);
      return;
    }
    const ctl = new AbortController();
    const timer = setTimeout(() => {
      searchPlaces(text, { signal: ctl.signal }).then(
        (found) => { setResults(found); setMessage(found.length ? null : "No matches. Try a landmark or street."); },
        () => { if (!ctl.signal.aborted) setMessage("Search is not available right now."); },
      );
    }, 300);
    return () => { clearTimeout(timer); ctl.abort(); };
  }, [text, value, searchable]);

  function useMyLocation() {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      onLocationDenied?.();
      setMessage("Location is not available. Enter a starting point.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => onChange({ id: "my-location", name: "My location", lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => { onLocationDenied?.(); setMessage("Location is off. Enter a starting point."); },
      { maximumAge: 60_000, timeout: 10_000 },
    );
  }

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id} className="input" value={text} placeholder={placeholder}
        autoComplete="off" inputMode="search"
        onChange={(e) => { setText(e.target.value); if (value) onChange(null); }}
      />
      {results.length > 0 ? (
        <ul className="suggestions" aria-label={`${label} suggestions`}>
          {results.map((p) => (
            <li key={p.id}>
              <button type="button" onClick={() => { onChange(p); setResults([]); }}>{p.name}</button>
            </li>
          ))}
        </ul>
      ) : null}
      {message ? <p className="small muted" role="status" style={{ marginTop: 6 }}>{message}</p> : null}
      <div className="chips" style={{ marginTop: 8 }}>
        {allowMyLocation ? (
          <button type="button" className="chip" onClick={useMyLocation}><SearchIcon /> Use my location</button>
        ) : null}
        {presets.map((p) => (
          <button key={p.id} type="button" className="chip" aria-pressed={value?.id === p.id} onClick={() => onChange(p)}>
            {p.name}
          </button>
        ))}
      </div>
      {!searchable ? (
        <p className="caption" style={{ marginTop: 6 }}>
          Address search needs a map key on this server. You can still pick the demo places above.
        </p>
      ) : null}
    </div>
  );
}
