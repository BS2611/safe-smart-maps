"use client";

import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode,
} from "react";

import { clearTrip, EMPTY_TRIP, loadTrip, saveTrip, type Trip } from "@/lib/trip";
import type { RoutesResponse } from "@/lib/types";

type TripContextValue = {
  trip: Trip;
  ready: boolean; // false until the saved trip has been read (avoids a flash of an empty form)
  updateTrip: (patch: Partial<Trip>) => void;
  resetTrip: () => void;
  getCached: (key: string) => RoutesResponse | undefined;
  putCached: (key: string, value: RoutesResponse) => void;
};

const TripContext = createContext<TripContextValue | null>(null);

export function TripProvider({ children, initialTrip }: { children: ReactNode; initialTrip?: Trip }) {
  const [trip, setTrip] = useState<Trip>(initialTrip ?? EMPTY_TRIP);
  const [ready, setReady] = useState(Boolean(initialTrip));
  const cache = useRef(new Map<string, RoutesResponse>());

  useEffect(() => {
    if (!initialTrip) {
      setTrip(loadTrip());
      setReady(true);
    }
  }, [initialTrip]);

  const updateTrip = useCallback((patch: Partial<Trip>) => {
    setTrip((current) => {
      const next = { ...current, ...patch };
      saveTrip(next);
      return next;
    });
  }, []);

  const resetTrip = useCallback(() => {
    clearTrip();
    cache.current.clear();
    setTrip(EMPTY_TRIP);
  }, []);

  const value = useMemo<TripContextValue>(() => ({
    trip, ready, updateTrip, resetTrip,
    getCached: (key) => cache.current.get(key),
    putCached: (key, v) => { cache.current.set(key, v); },
  }), [trip, ready, updateTrip, resetTrip]);

  return <TripContext.Provider value={value}>{children}</TripContext.Provider>;
}

export function useTrip(): TripContextValue {
  const ctx = useContext(TripContext);
  if (!ctx) throw new Error("useTrip must be used inside <TripProvider>");
  return ctx;
}
