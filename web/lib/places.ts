// Real places for the demo corridor (Palace of Fine Arts to Montgomery BART). These are map
// locations, not mock data. Search by address needs a Mapbox token (lib/geocode.ts).
import type { Place } from "./types";

export const DEMO_PLACES: Place[] = [
  { id: "palace-of-fine-arts", name: "Palace of Fine Arts", lat: 37.8029, lng: -122.4484 },
  { id: "montgomery-bart", name: "Montgomery BART Station", lat: 37.7894, lng: -122.4013 },
];

export const SAN_FRANCISCO_CENTER = { lat: 37.7793, lng: -122.4193 };
