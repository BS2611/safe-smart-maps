// What we check, in plain words. The weights must equal scoring/scoring_v1.json
// (lib/scoring-info.test.ts reads that file). Claims here must match what the backend really does.
export type FactorInfo = {
  id: string;
  label: string;
  weight: number; // percent
  description: string;
  source: string;
  estimate?: boolean;
};

export const FACTORS: FactorInfo[] = [
  {
    id: "open_places", label: "Open places", weight: 25,
    description: "Shops, cafes and restaurants that are open when you reach them, within about 50 m. 24-hour pharmacies, gas stations, stores and restaurants count more.",
    source: "Public business listings, fetched live",
  },
  {
    id: "lighting", label: "Lighting", weight: 20,
    description: "Streets marked as lit on OpenStreetMap. Open streetlight outage reports lower the score. Many streets have no lighting tag, and then we say not sure.",
    source: "OpenStreetMap, SF 311 streetlight reports",
  },
  {
    id: "main_road", label: "Main roads", weight: 15,
    description: "Main roads rather than alleys, paths or dead ends.",
    source: "OpenStreetMap",
  },
  {
    id: "help_points", label: "Help points", weight: 10,
    description: "A hospital, police station, fire station or 24-hour store within about 150 m.",
    source: "OpenStreetMap, public business listings",
  },
  {
    id: "transit", label: "Running transit", weight: 10,
    description: "A stop with service in the next 15 minutes. Transit schedules are not connected yet, so this shows as not sure.",
    source: "Transit schedules (511 / GTFS), not connected yet",
  },
  {
    id: "activity", label: "Activity estimate", weight: 10, estimate: true,
    description: "An estimate from the open places nearby and the time of day. It is not a count of people.",
    source: "Derived from open places and time of day",
  },
  {
    id: "incidents", label: "Past incidents", weight: 5,
    description: "Past incident reports, kept at a low weight on purpose: they can reflect policing patterns as much as the events.",
    source: "SF open data (police incident reports)",
  },
  {
    id: "turns", label: "Turns & dead ends", weight: 5,
    description: "Fewer sharp turns and no underpasses make a route easier to follow.",
    source: "Route shape, OpenStreetMap",
  },
];

export const CONTINUITY_RULES = {
  coverageTarget: 80,
  coverageRadiusM: 75,
  gapLimitM: 150,
  windowM: 200,
};

export const SCORE_FORMULA =
  "Route score = 50% × average segment score + 50% × lowest 200 m stretch − a penalty for any empty stretch over 150 m";

export function factorLabel(id: string): string {
  return FACTORS.find((f) => f.id === id)?.label ?? id;
}
