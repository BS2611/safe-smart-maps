import { basicCenterForHeading, haversineM } from "./geo";
import { StreetViewError, type StreetViewHandle, type StreetViewMount, type StreetViewPhoto, type StreetViewProvider } from "./types";

const GRAPH = "https://graph.mapillary.com/images";

type MapillaryViewer = {
  moveTo: (id: string) => Promise<unknown>;
  setCenter: (center: number[]) => void;
  setTransitionMode: (mode: number) => void;
  getBearing: () => Promise<number>;
  on: (type: "bearing", handler: (event: { bearing: number }) => void) => void;
  off: (type: "bearing", handler: (event: { bearing: number }) => void) => void;
  remove: () => void;
  resize: () => void;
};

type MapillaryModule = {
  Viewer: new (options: {
    accessToken: string;
    container: HTMLElement;
    imageId: string;
    component: Record<string, boolean>;
  }) => MapillaryViewer;
  TransitionMode: { Instantaneous: number };
};

function geometryOf(value: unknown): [number, number] | null {
  if (!value || typeof value !== "object") return null;
  const coords = (value as { coordinates?: unknown }).coordinates;
  if (!Array.isArray(coords) || coords.length < 2) return null;
  const lng = coords[0];
  const lat = coords[1];
  if (typeof lng !== "number" || typeof lat !== "number") return null;
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
  return [lng, lat];
}

/** Read a Graph API image list. Drops rows that have no id or no position. */
export function parseMapillaryImages(body: unknown): StreetViewPhoto[] {
  if (!body || typeof body !== "object") return [];
  const data = (body as { data?: unknown }).data;
  if (!Array.isArray(data)) return [];
  const photos: StreetViewPhoto[] = [];
  for (const row of data) {
    if (!row || typeof row !== "object") continue;
    const rec = row as Record<string, unknown>;
    if (rec.id === undefined || rec.id === null || rec.id === "") continue;
    const geom = geometryOf(rec.computed_geometry) ?? geometryOf(rec.geometry);
    if (!geom) continue;
    const captured = typeof rec.captured_at === "number" && Number.isFinite(rec.captured_at)
      ? new Date(rec.captured_at).toISOString()
      : null;
    photos.push({
      provider: "mapillary",
      id: String(rec.id),
      lng: geom[0],
      lat: geom[1],
      compass: typeof rec.compass_angle === "number" && Number.isFinite(rec.compass_angle) ? rec.compass_angle : null,
      capturedAt: captured,
      isPano: rec.is_pano === true,
    });
  }
  return photos;
}

/** Prefer a panorama, then the photo closest to the point the person picked. */
export function chooseMapillaryPhoto(photos: StreetViewPhoto[], lng: number, lat: number): StreetViewPhoto | null {
  if (photos.length === 0) return null;
  const ranked = [...photos].sort((a, b) => {
    if (a.isPano !== b.isPano) return a.isPano ? -1 : 1;
    return haversineM(a.lng, a.lat, lng, lat) - haversineM(b.lng, b.lat, lng, lat);
  });
  return ranked[0];
}

async function findNearest(token: string, lng: number, lat: number, signal?: AbortSignal): Promise<StreetViewPhoto | null> {
  const url = new URL(GRAPH);
  url.searchParams.set("fields", "id,computed_geometry,geometry,compass_angle,captured_at,is_pano");
  url.searchParams.set("closeto", `${lng},${lat}`);
  url.searchParams.set("radius", "80");
  url.searchParams.set("limit", "8");
  let res: Response;
  try {
    res = await fetch(url, { signal, headers: { Authorization: `OAuth ${token}` } });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new StreetViewError("failed");
  }
  if (res.status === 401 || res.status === 403) throw new StreetViewError("unavailable");
  if (!res.ok) throw new StreetViewError("failed");
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    throw new StreetViewError("failed");
  }
  return chooseMapillaryPhoto(parseMapillaryImages(body), lng, lat);
}

async function lookAlong(viewer: MapillaryViewer, photo: StreetViewPhoto, heading: number, onHeading: (degrees: number) => void) {
  await viewer.moveTo(photo.id);
  if (photo.isPano && photo.compass !== null) {
    viewer.setCenter(basicCenterForHeading(photo.compass, heading));
  }
  viewer.resize();
  const bearing = await viewer.getBearing();
  if (typeof bearing === "number" && Number.isFinite(bearing)) onHeading(bearing);
}

async function mount(token: string, args: StreetViewMount): Promise<StreetViewHandle> {
  const mod = await import("mapillary-js") as MapillaryModule;
  await import("mapillary-js/dist/mapillary.css");
  args.container.replaceChildren();
  const viewer = new mod.Viewer({
    accessToken: token,
    container: args.container,
    imageId: args.photo.id,
    component: {
      cover: true,
      attribution: true,
      bearing: false,
      sequence: false,
      direction: false,
      keyboard: false,
      slider: false,
    },
  });
  if (args.reducedMotion) viewer.setTransitionMode(mod.TransitionMode.Instantaneous);
  const onBearing = (event: { bearing: number }) => {
    if (typeof event?.bearing === "number" && Number.isFinite(event.bearing)) args.onHeading(event.bearing);
  };
  viewer.on("bearing", onBearing);
  const onResize = () => viewer.resize();
  window.addEventListener("resize", onResize);
  try {
    await lookAlong(viewer, args.photo, args.heading, args.onHeading);
  } catch {
    window.removeEventListener("resize", onResize);
    viewer.remove();
    args.container.replaceChildren();
    throw new StreetViewError("failed");
  }
  return {
    async moveTo(photo, heading) {
      try {
        await lookAlong(viewer, photo, heading, args.onHeading);
      } catch {
        throw new StreetViewError("failed");
      }
    },
    destroy() {
      window.removeEventListener("resize", onResize);
      viewer.off("bearing", onBearing);
      viewer.remove();
      args.container.replaceChildren();
    },
  };
}

export function createMapillaryProvider(token: string): StreetViewProvider {
  const trimmed = token.trim();
  return {
    id: "mapillary",
    configured: trimmed.length > 0,
    findNearest: (lng, lat, signal) => findNearest(trimmed, lng, lat, signal),
    mount: (viewerArgs) => mount(trimmed, viewerArgs),
  };
}
