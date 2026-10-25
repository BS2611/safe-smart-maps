// Phone side of the watch relay (CONTRACTS.md "Watch relay endpoints"). The phone asks the backend
// for a pairing code, then polls for readings the watch sends. Nothing here touches storage.
import type { ReadingSource, WatchReading, WatchSource } from "./watch";

export type RelayOptions = { baseUrl?: string; fetchImpl?: typeof fetch; pollMs?: number };

export type PairingInfo = { tripId: string; pairCode: string; expiresInS: number };

export type RelayEvent = {
  id: number;
  type: "paired" | "bpm" | "prompt" | "alert_sent" | "ack";
  bpm?: number;
  ts?: string;
  source?: WatchSource;
  ok?: boolean;
  status?: string;
};

export type EventsResponse = {
  status: "waiting" | "paired";
  latest: { bpm: number; ts: string; source: WatchSource } | null;
  events: RelayEvent[];
  next_after: number;
};

export class RelayError extends Error {
  constructor(readonly kind: "NETWORK" | "NOT_FOUND" | "FAILED", message: string) {
    super(message);
  }
}

export const DEFAULT_POLL_MS = 2000;
export const LOST_AFTER_MS = 15_000;

function base(options: RelayOptions): string {
  return options.baseUrl ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function call(path: string, init: RequestInit, options: RelayOptions): Promise<Response> {
  const fetchImpl = options.fetchImpl ?? fetch;
  let res: Response;
  try {
    res = await fetchImpl(`${base(options)}${path}`, init);
  } catch {
    throw new RelayError("NETWORK", "Could not reach the server.");
  }
  if (res.status === 404) throw new RelayError("NOT_FOUND", "This watch check has ended.");
  if (!res.ok) throw new RelayError("FAILED", "The server could not do that. Try again.");
  return res;
}

export async function startPairing(options: RelayOptions = {}): Promise<PairingInfo> {
  const res = await call("/v1/trips/pair", { method: "POST" }, options);
  const json = (await res.json()) as { trip_id: string; pair_code: string; expires_in_s: number };
  return { tripId: json.trip_id, pairCode: json.pair_code, expiresInS: json.expires_in_s };
}

export async function fetchEvents(tripId: string, after: number, options: RelayOptions = {}): Promise<EventsResponse> {
  const res = await call(`/v1/trips/${encodeURIComponent(tripId)}/events?after=${after}`, {}, options);
  return (await res.json()) as EventsResponse;
}

/** Deletes the trip and its readings on the server. Safe to call when leaving the page. */
export async function endTrip(tripId: string, options: RelayOptions = {}): Promise<void> {
  try {
    await call(`/v1/trips/${encodeURIComponent(tripId)}/end`, { method: "POST", keepalive: true }, options);
  } catch {
    // already gone or offline: the server also deletes idle trips after 30 minutes
  }
}

export type RelayHandlers = {
  onEvent?: (event: RelayEvent, status: EventsResponse["status"]) => void;
  onError?: (error: RelayError) => void;
};

/** A ReadingSource that polls the relay. Heart-rate events become readings; the rest go to onEvent. */
export function createRelaySource(tripId: string, handlers: RelayHandlers = {}, options: RelayOptions = {}): ReadingSource {
  let stopped = true;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let after = 0;

  return {
    start(onReading: (reading: WatchReading) => void) {
      if (!stopped) return;
      stopped = false;
      const tick = async () => {
        try {
          const out = await fetchEvents(tripId, after, options);
          if (stopped) return;
          after = out.next_after;
          for (const e of out.events) {
            if (e.type === "bpm" && e.bpm !== undefined && e.ts && e.source) {
              onReading({ bpm: e.bpm, ts: e.ts, source: e.source });
            }
            handlers.onEvent?.(e, out.status);
          }
        } catch (err) {
          if (stopped) return;
          const error = err instanceof RelayError ? err : new RelayError("FAILED", "Something went wrong.");
          handlers.onError?.(error);
          if (error.kind === "NOT_FOUND") {
            stopped = true;
            return;
          }
        }
        if (!stopped) timer = setTimeout(tick, options.pollMs ?? DEFAULT_POLL_MS);
      };
      void tick();
    },
    stop() {
      stopped = true;
      if (timer) clearTimeout(timer);
      timer = null;
    },
  };
}
