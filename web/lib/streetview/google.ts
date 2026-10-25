import { StreetViewError, type StreetViewHandle, type StreetViewMount, type StreetViewPhoto, type StreetViewProvider } from "./types";

type LatLngLike = { lat: () => number; lng: () => number } | { lat: number; lng: number };

type PanoData = {
  location?: { pano?: string; latLng?: LatLngLike };
  imageDate?: string;
};

type Pano = {
  setPosition: (p: { lat: number; lng: number }) => void;
  setPov: (p: { heading: number; pitch: number }) => void;
  getPov: () => { heading?: number; pitch?: number };
  setVisible: (v: boolean) => void;
  addListener: (name: string, cb: () => void) => { remove: () => void };
};

type GoogleMaps = {
  maps: {
    StreetViewPanorama: new (el: HTMLElement, opts: Record<string, unknown>) => Pano;
    StreetViewService: new () => {
      getPanorama: (
        req: { location: { lat: number; lng: number }; radius: number; source?: string },
        cb: (data: PanoData | null, status: string) => void,
      ) => void;
    };
    StreetViewSource?: { OUTDOOR?: string };
  };
};

declare global {
  interface Window {
    google?: GoogleMaps;
  }
}

let loading: Promise<void> | null = null;

function mapsReady(): boolean {
  return typeof window !== "undefined" && typeof window.google?.maps?.StreetViewService === "function";
}

/** Load the Maps JavaScript API once. The key stays in the script URL and is never copied into errors. */
export function loadGoogleMaps(key: string): Promise<void> {
  if (mapsReady()) return Promise.resolve();
  if (typeof document === "undefined") return Promise.reject(new StreetViewError("failed"));
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.async = true;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly`;
    script.onload = () => {
      if (mapsReady()) resolve();
      else {
        loading = null;
        reject(new StreetViewError("failed"));
      }
    };
    script.onerror = () => {
      loading = null;
      reject(new StreetViewError("failed"));
    };
    document.head.appendChild(script);
  });
  return loading;
}

function readLatLng(value: LatLngLike | undefined): { lng: number; lat: number } | null {
  if (!value) return null;
  const lat = typeof value.lat === "function" ? value.lat() : value.lat;
  const lng = typeof value.lng === "function" ? value.lng() : value.lng;
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lng, lat };
}

function photoFromPano(data: PanoData | null, fallback: { lng: number; lat: number }): StreetViewPhoto | null {
  const id = data?.location?.pano;
  if (!id) return null;
  const at = readLatLng(data?.location?.latLng) ?? fallback;
  const month = typeof data?.imageDate === "string" && /^\d{4}-\d{2}$/.test(data.imageDate) ? data.imageDate : null;
  return {
    provider: "google",
    id,
    lng: at.lng,
    lat: at.lat,
    compass: null,
    capturedAt: month,
    isPano: true,
  };
}

async function findNearest(key: string, lng: number, lat: number): Promise<StreetViewPhoto | null> {
  await loadGoogleMaps(key);
  const maps = window.google?.maps;
  if (!maps) throw new StreetViewError("failed");
  const service = new maps.StreetViewService();
  const source = maps.StreetViewSource?.OUTDOOR;
  return new Promise((resolve, reject) => {
    try {
      service.getPanorama(
        { location: { lat, lng }, radius: 50, ...(source ? { source } : {}) },
        (data, status) => {
          if (status !== "OK") {
            resolve(null);
            return;
          }
          resolve(photoFromPano(data, { lng, lat }));
        },
      );
    } catch {
      reject(new StreetViewError("failed"));
    }
  });
}

function aim(pano: Pano, photo: StreetViewPhoto, heading: number, onHeading: (degrees: number) => void) {
  pano.setPosition({ lat: photo.lat, lng: photo.lng });
  pano.setPov({ heading, pitch: 0 });
  onHeading(heading);
}

async function mount(key: string, args: StreetViewMount): Promise<StreetViewHandle> {
  await loadGoogleMaps(key);
  const Ctor = window.google?.maps?.StreetViewPanorama;
  if (!Ctor) throw new StreetViewError("failed");
  args.container.replaceChildren();
  const pano = new Ctor(args.container, {
    position: { lat: args.photo.lat, lng: args.photo.lng },
    pov: { heading: args.heading, pitch: 0 },
    zoom: 1,
    addressControl: false,
    fullscreenControl: false,
    linksControl: false,
    clickToGo: false,
    panControl: false,
    zoomControl: false,
    motionTracking: false,
    motionTrackingControl: false,
    enableCloseButton: false,
    disableDefaultUI: true,
  });
  pano.setPov({ heading: args.heading, pitch: 0 });
  const listener = pano.addListener("pov_changed", () => {
    const heading = pano.getPov()?.heading;
    if (typeof heading === "number" && Number.isFinite(heading)) args.onHeading(heading);
  });
  args.onHeading(args.heading);
  return {
    async moveTo(photo, heading) {
      aim(pano, photo, heading, args.onHeading);
    },
    destroy() {
      listener.remove();
      pano.setVisible(false);
      args.container.replaceChildren();
    },
  };
}

export function createGoogleProvider(key: string): StreetViewProvider {
  const trimmed = key.trim();
  return {
    id: "google",
    configured: trimmed.length > 0,
    findNearest: (lng, lat) => findNearest(trimmed, lng, lat),
    mount: (viewerArgs) => mount(trimmed, viewerArgs),
  };
}
