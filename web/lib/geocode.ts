// Address search through Mapbox Geocoding (browser token, URL-restricted, from env).
import { SAN_FRANCISCO_CENTER } from "./places";
import type { Place } from "./types";

export function hasGeocoding(token: string | undefined = process.env.NEXT_PUBLIC_MAPBOX_TOKEN): boolean {
  return Boolean(token);
}

export function parseGeocode(payload: unknown): Place[] {
  const features = (payload as { features?: unknown[] } | null)?.features;
  if (!Array.isArray(features)) return [];
  const out: Place[] = [];
  for (const f of features) {
    const feature = f as {
      id?: string;
      properties?: { name?: string; full_address?: string; place_formatted?: string };
      geometry?: { coordinates?: [number, number] };
    };
    const coords = feature.geometry?.coordinates;
    const name = feature.properties?.name;
    if (!coords || coords.length < 2 || !name) continue;
    const detail = feature.properties?.place_formatted;
    out.push({
      id: feature.id ?? `${coords[1]},${coords[0]}`,
      name: detail ? `${name}, ${detail}` : name,
      lat: coords[1],
      lng: coords[0],
    });
  }
  return out;
}

export async function searchPlaces(
  query: string,
  options: { token?: string; fetchImpl?: typeof fetch; signal?: AbortSignal } = {},
): Promise<Place[]> {
  const token = options.token ?? process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  const text = query.trim();
  if (!token || text.length < 3) return [];
  const fetchImpl = options.fetchImpl ?? fetch;
  const url = new URL("https://api.mapbox.com/search/geocode/v6/forward");
  url.searchParams.set("q", text);
  url.searchParams.set("limit", "5");
  url.searchParams.set("country", "us");
  url.searchParams.set("proximity", `${SAN_FRANCISCO_CENTER.lng},${SAN_FRANCISCO_CENTER.lat}`);
  url.searchParams.set("access_token", token);
  const res = await fetchImpl(url.toString(), { signal: options.signal });
  if (!res.ok) throw new Error(`Search failed (${res.status})`);
  return parseGeocode(await res.json());
}
