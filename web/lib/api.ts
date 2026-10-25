// Client for the backend (docs/agent-context/CONTRACTS.md). Responses are validated with zod.
import { hourIn } from "./time";
import { toRequestBody, type Trip } from "./trip";
import {
  ErrorResponseSchema, RoutesResponseSchema, type ErrorCode, type RoutesResponse,
} from "./types";

export class ApiError extends Error {
  constructor(public code: ErrorCode | "NETWORK" | "BAD_RESPONSE" | "CANCELLED", message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export type FetchOptions = {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
  now?: Date;
  devFixtures?: boolean;
  timeoutMs?: number;
};

export function devFixturesEnabled(): boolean {
  return process.env.NEXT_PUBLIC_DEV_FIXTURES === "1";
}

/** Dev-only sample data: picks the 8 PM or the 1 AM sample by the chosen hour. Off by default. */
export function fixturePath(departISO: string | Date): string {
  const hour = hourIn(new Date(departISO));
  return hour >= 0 && hour < 5 ? "/dev-fixtures/routes_response_1am.json" : "/dev-fixtures/routes_response.json";
}

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "NO_ROUTE": return "We could not find a walking route between these places.";
      case "BAD_REQUEST": return error.message;
      case "NOT_CONFIGURED": return "The route service is not set up yet. Please try again later.";
      case "UPSTREAM_TIMEOUT": return "The route service took too long. Try again.";
      case "UPSTREAM_ERROR": return "The route service had a problem. Try again.";
      case "NETWORK": return "We could not reach the server. Check your connection and try again.";
      case "CANCELLED": return "Check cancelled.";
      default: return "The server sent something we could not read.";
    }
  }
  return "Something went wrong. Try again.";
}

export async function fetchRoutes(trip: Trip, options: FetchOptions = {}): Promise<RoutesResponse> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const body = toRequestBody(trip, options.now);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), options.timeoutMs ?? 90_000);
  const outer = options.signal;
  const onAbort = () => controller.abort("cancelled");
  outer?.addEventListener("abort", onAbort);
  try {
    const useFixtures = options.devFixtures ?? devFixturesEnabled();
    const url = useFixtures
      ? fixturePath(body.depart_time)
      : `${options.baseUrl ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/v1/routes`;
    const init: RequestInit = useFixtures
      ? { signal: controller.signal }
      : {
          method: "POST", signal: controller.signal,
          headers: { "content-type": "application/json" }, body: JSON.stringify(body),
        };
    let res: Response;
    try {
      res = await fetchImpl(url, init);
    } catch {
      if (outer?.aborted) throw new ApiError("CANCELLED", "Check cancelled.");
      if (controller.signal.aborted) throw new ApiError("UPSTREAM_TIMEOUT", "The check took too long.");
      throw new ApiError("NETWORK", "Network error");
    }
    let json: unknown;
    try {
      json = await res.json();
    } catch {
      throw new ApiError("BAD_RESPONSE", "Response was not JSON");
    }
    if (!res.ok) {
      const parsed = ErrorResponseSchema.safeParse(json);
      if (parsed.success) throw new ApiError(parsed.data.error.code, parsed.data.error.message);
      throw new ApiError("BAD_RESPONSE", `HTTP ${res.status}`);
    }
    const parsed = RoutesResponseSchema.safeParse(json);
    if (!parsed.success) throw new ApiError("BAD_RESPONSE", "Response did not match the contract");
    return parsed.data;
  } finally {
    clearTimeout(timer);
    outer?.removeEventListener("abort", onAbort);
  }
}
