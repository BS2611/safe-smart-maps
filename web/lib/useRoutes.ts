"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useTrip } from "@/components/TripProvider";

import { ApiError, fetchRoutes, type FetchOptions } from "./api";
import { isReady, toRequestBody, type Trip } from "./trip";
import type { RoutesResponse } from "./types";

export type RoutesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: RoutesResponse }
  | { status: "error"; error: ApiError | Error };

export function requestKey(trip: Trip): string {
  return JSON.stringify(toRequestBody(trip, new Date(0)));
}

/** Loads routes for `trip` (cached per request), with cancel and retry. */
export function useRoutes(trip: Trip, options: FetchOptions = {}) {
  const { getCached, putCached } = useTrip();
  const [state, setState] = useState<RoutesState>({ status: "idle" });
  const controller = useRef<AbortController | null>(null);
  const [attempt, setAttempt] = useState(0);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const ready = isReady(trip);
  const key = ready ? requestKey(trip) : "";

  useEffect(() => {
    if (!ready) {
      setState({ status: "idle" });
      return;
    }
    const cached = getCached(key);
    if (cached) {
      setState({ status: "success", data: cached });
      return;
    }
    const ctl = new AbortController();
    controller.current = ctl;
    setState({ status: "loading" });
    fetchRoutes(trip, { ...optionsRef.current, signal: ctl.signal }).then(
      (data) => {
        if (ctl.signal.aborted) return;
        putCached(key, data);
        setState({ status: "success", data });
      },
      (error: unknown) => {
        if (ctl.signal.aborted && !(error instanceof ApiError && error.code === "UPSTREAM_TIMEOUT")) return;
        setState({ status: "error", error: error instanceof Error ? error : new Error("failed") });
      },
    );
    return () => ctl.abort();
    // `trip` is represented by `key`; getCached/putCached are stable enough for this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, ready, attempt]);

  const cancel = useCallback(() => {
    controller.current?.abort();
    setState({ status: "error", error: new ApiError("CANCELLED", "Check cancelled.") });
  }, []);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { state, cancel, retry };
}
