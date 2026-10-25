// What the server checks while it works, and which checks the response says were not available.
// The server runs these checks in parallel and answers once, so the app cannot show real percentages.
// Before the answer every check shows "Checking"; after it, the response's warnings decide the status.
export type SourceStatus = "checking" | "done" | "unavailable";

export type SourceInfo = {
  id: string;
  title: string;
  detail: string;
  warningPrefix?: string; // matches the start of a warning from the server
};

export const SOURCES: SourceInfo[] = [
  { id: "routes", title: "Finding walking routes", detail: "Several candidate routes on the pedestrian network" },
  {
    id: "places", title: "Checking what's open when you arrive", detail: "Live business listings and their hours",
    warningPrefix: "Live business listings",
  },
  {
    id: "lighting", title: "Checking lighting and main roads", detail: "OpenStreetMap and streetlight reports",
    warningPrefix: "Street and lighting map data",
  },
  {
    id: "transit", title: "Checking transit", detail: "Transit schedules", warningPrefix: "Transit schedules",
  },
  { id: "reasons", title: "Preparing route reasons", detail: "Plain-language summary of each route" },
];

export function sourceStatuses(
  state: "loading" | "success", warnings: string[] = [],
): Record<string, SourceStatus> {
  const out: Record<string, SourceStatus> = {};
  for (const s of SOURCES) {
    if (state === "loading") out[s.id] = "checking";
    else out[s.id] = s.warningPrefix && warnings.some((w) => w.startsWith(s.warningPrefix as string))
      ? "unavailable" : "done";
  }
  return out;
}

export const STATUS_TEXT: Record<SourceStatus, string> = {
  checking: "Checking", done: "Done", unavailable: "Not sure",
};
