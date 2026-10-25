// Response shapes from docs/agent-context/CONTRACTS.md. Parsed at runtime so a changed or partial
// response becomes a clear error instead of a broken screen.
import { z } from "zod";

export const BandSchema = z.enum(["green", "yellow", "red", "unknown"]);
export const ConfidenceSchema = z.enum(["high", "low", "unknown"]);
export const LabelSchema = z.enum(["safest", "balanced", "fastest"]);

const Point = z.tuple([z.number(), z.number()]);

export const SegmentSchema = z.object({
  segment_id: z.string(),
  start: Point,
  end: Point,
  length_m: z.number(),
  arrival_time: z.string(),
  score: z.number().nullable(),
  band: BandSchema,
  factors: z.record(z.string(), z.number().nullable()),
  reasons: z.array(z.string()),
  data_fetched_at: z.string().nullable(),
  confidence: ConfidenceSchema,
});

export const RouteSchema = z.object({
  label: LabelSchema,
  also_labels: z.array(LabelSchema),
  route_id: z.string(),
  via: z.array(z.string()),
  duration_min: z.number(),
  extra_min: z.number(),
  distance_m: z.number(),
  route_score: z.number().nullable(),
  continuity: z.object({
    coverage_pct: z.number().nullable(),
    longest_gap_m: z.number(),
    longest_gap_note: z.string().nullable(),
    worst_window_score: z.number().nullable(),
  }),
  open_places_count: z.number().nullable(),
  nearest_help_point: z.object({ name: z.string(), distance_m: z.number() }).nullable(),
  geometry: z.object({ type: z.literal("LineString"), coordinates: z.array(Point) }),
  segments: z.array(SegmentSchema),
  explanation: z.string(),
  explanation_source: z.enum(["ai", "template"]),
});

export const RoutesResponseSchema = z.object({
  api_version: z.string(),
  scoring_version: z.string(),
  data_fetched_at: z.string().nullable(),
  routes: z.array(RouteSchema),
  warnings: z.array(z.string()),
});

export const ErrorResponseSchema = z.object({
  error: z.object({
    code: z.enum(["NO_ROUTE", "UPSTREAM_TIMEOUT", "UPSTREAM_ERROR", "BAD_REQUEST", "NOT_CONFIGURED"]),
    message: z.string(),
  }),
});

export type Band = z.infer<typeof BandSchema>;
export type Label = z.infer<typeof LabelSchema>;
export type Segment = z.infer<typeof SegmentSchema>;
export type Route = z.infer<typeof RouteSchema>;
export type RoutesResponse = z.infer<typeof RoutesResponseSchema>;
export type ErrorCode = z.infer<typeof ErrorResponseSchema>["error"]["code"];

export type LatLng = { lat: number; lng: number };
export type Place = { id: string; name: string; lat: number; lng: number };
