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
    id: "open_places", label: "Open places", weight: 22,
    description: "Shops, cafes and restaurants that are open when you reach them, within about 50 m. 24-hour pharmacies, gas stations, stores and restaurants count more.",
    source: "Public business listings, fetched live",
  },
  {
    id: "lighting", label: "Lighting", weight: 22,
    description: "Streets tagged as lit, plus nearby street lamps. An open streetlight outage lowers the score. A missing lighting tag stays not sure. It is never treated as unlit.",
    source: "OpenStreetMap lit tags and street lamps, SF 311 open outages",
  },
  {
    id: "main_road", label: "Main roads", weight: 13,
    description: "Main roads rather than alleys, paths or dead ends.",
    source: "OpenStreetMap",
  },
  {
    id: "help_points", label: "Help points", weight: 10,
    description: "A hospital, police station, fire station or 24-hour store within about 150 m.",
    source: "OpenStreetMap, public business listings",
  },
  {
    id: "transit", label: "Running transit", weight: 12,
    description: "A stop with a departure in the next 15 minutes. If no schedule feed is configured, this shows as not sure.",
    source: "SF Muni and BART GTFS, when a feed is configured",
  },
  {
    id: "activity", label: "Activity estimate", weight: 8, estimate: true,
    description: "An estimate of how busy the street is, from nearby shops and busy places on the map and the time of day. It is not a count of people.",
    source: "OpenStreetMap places and time of day",
  },
  {
    id: "incidents", label: "Past incidents", weight: 5,
    description: "Past incident reports, kept at a low weight on purpose: they can reflect policing patterns as much as the events.",
    source: "SF open data (police incident reports)",
  },
  {
    id: "turns", label: "Turns & dead ends", weight: 8,
    description: "How sharp the turn is. A turn on a street tagged as unlit counts as a dark turn. Unknown lighting is not treated as dark. An underpass lowers the score.",
    source: "Route shape and OpenStreetMap tunnel tags",
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
