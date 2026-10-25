// Street-level photos. Mapillary is the provider we ship. Google is the same
// interface, used only when a browser key is set.

export type StreetViewProviderId = "mapillary" | "google";

export type StreetViewPhoto = {
  provider: StreetViewProviderId;
  id: string;
  lng: number;
  lat: number;
  /** Camera compass, degrees clockwise from north. Null when the source did not say. */
  compass: number | null;
  /** ISO time, or a YYYY-MM month when that is all the source has. */
  capturedAt: string | null;
  isPano: boolean;
};

export type StreetViewMount = {
  container: HTMLElement;
  photo: StreetViewPhoto;
  /** Direction to look, degrees clockwise from north, along the walk. */
  heading: number;
  reducedMotion: boolean;
  onHeading: (degrees: number) => void;
};

export type StreetViewHandle = {
  moveTo: (photo: StreetViewPhoto, heading: number) => Promise<void>;
  destroy: () => void;
};

export interface StreetViewProvider {
  id: StreetViewProviderId;
  /** True only when the env key for this provider is non-empty. */
  configured: boolean;
  findNearest: (lng: number, lat: number, signal?: AbortSignal) => Promise<StreetViewPhoto | null>;
  mount: (args: StreetViewMount) => Promise<StreetViewHandle>;
}

export class StreetViewError extends Error {
  readonly kind: "unavailable" | "failed";

  constructor(kind: "unavailable" | "failed") {
    super(kind === "unavailable" ? "Street view is unavailable." : "Street view could not load this spot.");
    this.name = "StreetViewError";
    this.kind = kind;
  }
}
