// Compass and map rotation. 0 is north, degrees clockwise.
import { normalizeDegrees } from "./geo";

export type HeadingMode = "heading-up" | "north-up";
export type HeadingSource = "compass" | "course" | "none";

export type OrientationSample = {
  alpha: number | null;
  absolute?: boolean;
  /** iOS Safari compass, degrees clockwise from north. */
  webkitCompassHeading?: number | null;
};

/**
 * Compass heading from a deviceorientation event.
 * iOS reports webkitCompassHeading. Elsewhere, absolute alpha is counter-clockwise from north.
 * A relative alpha (no absolute compass) is not a heading.
 */
export function headingFromOrientation(sample: OrientationSample): number | null {
  const webkit = sample.webkitCompassHeading;
  if (typeof webkit === "number" && Number.isFinite(webkit)) return normalizeDegrees(webkit);
  if (typeof sample.alpha !== "number" || !Number.isFinite(sample.alpha)) return null;
  if (!sample.absolute) return null;
  return normalizeDegrees(360 - sample.alpha);
}

/** Compass first. GPS course only when the compass did not answer. Negative course means unknown. */
export function chooseHeading(compass: number | null, course: number | null): { degrees: number | null; source: HeadingSource } {
  if (typeof compass === "number" && Number.isFinite(compass)) {
    return { degrees: normalizeDegrees(compass), source: "compass" };
  }
  if (typeof course === "number" && Number.isFinite(course) && course >= 0) {
    return { degrees: normalizeDegrees(course), source: "course" };
  }
  return { degrees: null, source: "none" };
}

/** Mapbox bearing: the compass direction that points to the top of the screen. */
export function mapBearing(degrees: number | null, mode: HeadingMode): number {
  if (mode === "north-up" || degrees === null) return 0;
  return normalizeDegrees(degrees);
}

/**
 * Screen rotation of the user arrow. Heading-up keeps the arrow pointing up
 * because the map has already turned. North-up rotates the arrow.
 */
export function arrowRotation(degrees: number | null, mode: HeadingMode): number {
  if (degrees === null || mode === "heading-up") return 0;
  return normalizeDegrees(degrees);
}
