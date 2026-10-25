import { createGoogleProvider } from "./google";
import { createMapillaryProvider } from "./mapillary";
import type { StreetViewProvider } from "./types";

export type StreetViewEnv = {
  googleKey?: string;
  mapillaryToken?: string;
};

/**
 * Google Street View when NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is set.
 * Otherwise Mapillary (NEXT_PUBLIC_MAPILLARY_TOKEN). An empty token still
 * returns the Mapillary provider with configured=false.
 */
export function selectStreetViewProvider(env?: StreetViewEnv): StreetViewProvider {
  const googleKey = (env?.googleKey ?? process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim();
  const mapillaryToken = (env?.mapillaryToken ?? process.env.NEXT_PUBLIC_MAPILLARY_TOKEN ?? "").trim();
  if (googleKey) return createGoogleProvider(googleKey);
  return createMapillaryProvider(mapillaryToken);
}

export function streetViewSourceName(id: StreetViewProvider["id"]): string {
  return id === "google" ? "Google Street View" : "Mapillary";
}
