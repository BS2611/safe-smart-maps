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
  { id: "routes", title: "Finding walking routes", detail: "A few walks on streets you can use" },
  {
    id: "places", title: "Checking what's open when you arrive", detail: "Places and their posted hours",
    warningPrefix: "Live business listings",
  },
  {
    id: "lighting", title: "Checking lighting and main roads", detail: "Street maps and lighting reports",
    warningPrefix: "Street and lighting map data",
  },
  {
    id: "transit", title: "Checking transit", detail: "Bus and train times", warningPrefix: "Transit schedules",
  },
  { id: "reasons", title: "Preparing route reasons", detail: "A short reason for each route" },
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
