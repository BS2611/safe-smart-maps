// Location, compass, and optional vibration. Missing permission or a missing sensor is a status, not a crash.
import { Capacitor } from "@capacitor/core";

import { headingFromOrientation, type OrientationSample } from "./heading";

export type GeoFix = {
  lng: number;
  lat: number;
  accuracyM: number | null;
  /** Direction of travel, or the platform heading, degrees clockwise from north. Null when unknown. */
  course: number | null;
};

export type LocationStatus = "live" | "denied" | "unavailable";
export type CompassStatus = "on" | "denied" | "unavailable";

type Stop = { stop: () => void };

function finiteHeading(value: number | null | undefined): number | null {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return null;
  return value;
}

export async function watchLocation(
  onFix: (fix: GeoFix) => void,
  onStatus: (status: LocationStatus) => void,
): Promise<Stop> {
  try {
    if (Capacitor.isNativePlatform()) {
      const { Geolocation } = await import("@capacitor/geolocation");
      const perm = await Geolocation.requestPermissions();
      if (perm.location !== "granted" && perm.coarseLocation !== "granted") {
        onStatus("denied");
        return { stop() {} };
      }
      const id = await Geolocation.watchPosition(
        { enableHighAccuracy: true, timeout: 12_000, maximumAge: 1_000 },
        (pos, err) => {
          if (err || !pos) return;
          const course = finiteHeading(pos.coords.trueHeading) ?? finiteHeading(pos.coords.heading);
          onFix({
            lng: pos.coords.longitude,
            lat: pos.coords.latitude,
            accuracyM: pos.coords.accuracy,
            course,
          });
          onStatus("live");
        },
      );
      return { stop: () => { void Geolocation.clearWatch({ id }); } };
    }
  } catch {
    // The browser geolocation API is the fallback.
  }
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    onStatus("unavailable");
    return { stop() {} };
  }
  const id = navigator.geolocation.watchPosition(
    (pos) => {
      onFix({
        lng: pos.coords.longitude,
        lat: pos.coords.latitude,
        accuracyM: Number.isFinite(pos.coords.accuracy) ? pos.coords.accuracy : null,
        course: finiteHeading(pos.coords.heading),
      });
      onStatus("live");
    },
    (err) => onStatus(err.code === 1 ? "denied" : "unavailable"),
    { enableHighAccuracy: true, maximumAge: 1_000, timeout: 12_000 },
  );
  return { stop: () => navigator.geolocation.clearWatch(id) };
}

type OrientationEventLike = DeviceOrientationEvent & { webkitCompassHeading?: number };

function sampleOf(event: OrientationEventLike): OrientationSample {
  return {
    alpha: event.alpha,
    absolute: event.absolute,
    webkitCompassHeading: event.webkitCompassHeading,
  };
}

/**
 * Start the compass. On iOS this must be called from a tap, because the permission prompt
 * is only allowed in a user gesture. Capacitor Motion forwards deviceorientation.
 */
export async function watchCompass(onHeading: (degrees: number | null) => void): Promise<{ stop: () => void; status: CompassStatus }> {
  const Orientation = typeof DeviceOrientationEvent === "undefined"
    ? undefined
    : DeviceOrientationEvent as typeof DeviceOrientationEvent & { requestPermission?: () => Promise<string> };
  if (Orientation && typeof Orientation.requestPermission === "function") {
    try {
      const result = await Orientation.requestPermission();
      if (result !== "granted") return { stop() {}, status: "denied" };
    } catch {
      return { stop() {}, status: "denied" };
    }
  }
  try {
    const { Motion } = await import("@capacitor/motion");
    const handle = await Motion.addListener("orientation", (event) => {
      const raw = event as unknown as OrientationEventLike;
      onHeading(headingFromOrientation(sampleOf(raw)));
    });
    return { stop: () => { void handle.remove(); }, status: "on" };
  } catch {
    if (typeof window === "undefined" || typeof DeviceOrientationEvent === "undefined") {
      return { stop() {}, status: "unavailable" };
    }
    const listener = (event: Event) => onHeading(headingFromOrientation(sampleOf(event as OrientationEventLike)));
    window.addEventListener("deviceorientation", listener);
    return {
      stop: () => window.removeEventListener("deviceorientation", listener),
      status: "on",
    };
  }
}

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** A short vibration on a turn. Skipped when reduced motion is on, or when the device cannot vibrate. */
export async function buzz(enabled: boolean): Promise<void> {
  if (!enabled || prefersReducedMotion()) return;
  try {
    if (Capacitor.isNativePlatform()) {
      const { Haptics, ImpactStyle } = await import("@capacitor/haptics");
      await Haptics.impact({ style: ImpactStyle.Medium });
      return;
    }
  } catch {
    // Browser vibration below.
  }
  try {
    navigator.vibrate?.(24);
  } catch {
    // No vibrator.
  }
}
