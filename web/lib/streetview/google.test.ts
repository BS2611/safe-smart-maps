import { vi } from "vitest";

import { createGoogleProvider, loadGoogleMaps } from "./google";
import { StreetViewError } from "./types";

type Pano = {
  setPosition: ReturnType<typeof vi.fn>;
  setPov: ReturnType<typeof vi.fn>;
  getPov: () => { heading: number; pitch: number };
  setVisible: ReturnType<typeof vi.fn>;
  addListener: (name: string, cb: () => void) => { remove: ReturnType<typeof vi.fn> };
  listeners: Record<string, () => void>;
};

function installGoogle(status = "OK", data?: { pano?: string; lat?: number; lng?: number; imageDate?: string } | null) {
  const pano: Pano = {
    setPosition: vi.fn(),
    setPov: vi.fn(),
    getPov: () => ({ heading: 15, pitch: 0 }),
    setVisible: vi.fn(),
    listeners: {},
    addListener(name, cb) {
      this.listeners[name] = cb;
      return { remove: vi.fn() };
    },
  };
  const getPanorama = vi.fn((
    req: { location: { lat: number; lng: number } },
    cb: (row: unknown, status: string) => void,
  ) => {
    if (data === null) {
      cb(null, status);
      return;
    }
    const row = data ?? { pano: "pano-1", lat: req.location.lat, lng: req.location.lng, imageDate: "2024-06" };
    cb({
      location: row.pano ? {
        pano: row.pano,
        latLng: { lat: () => row.lat ?? req.location.lat, lng: () => row.lng ?? req.location.lng },
      } : { latLng: { lat: row.lat, lng: row.lng } },
      imageDate: row.imageDate,
    }, status);
  });
  window.google = {
    maps: {
      StreetViewPanorama: vi.fn(function () { return pano; }),
      StreetViewService: vi.fn(function () { return { getPanorama }; }),
      StreetViewSource: { OUTDOOR: "outdoor" },
    },
  } as unknown as Window["google"];
  return { pano, getPanorama };
}

describe("Google Street View provider", () => {
  afterEach(() => {
    delete window.google;
    document.querySelectorAll("script").forEach((node) => node.remove());
  });

  it("does nothing until a key is present, then reads a panorama", async () => {
    expect(createGoogleProvider("  ").configured).toBe(false);
    const { getPanorama } = installGoogle();
    const provider = createGoogleProvider(" browser-key ");
    expect(provider.configured).toBe(true);
    const hit = await provider.findNearest(-122.4, 37.8);
    expect(hit).toMatchObject({ provider: "google", id: "pano-1", isPano: true, capturedAt: "2024-06" });
    expect(getPanorama).toHaveBeenCalled();
    const request = getPanorama.mock.calls[0][0] as { source?: string };
    expect(request.source).toBe("outdoor");
  });

  it("returns null when coverage is missing or the panorama has no id", async () => {
    installGoogle("ZERO_RESULTS");
    const provider = createGoogleProvider("browser-key");
    expect(await provider.findNearest(1, 2)).toBeNull();
    delete window.google;
    installGoogle("OK", { lat: 2, lng: 1, imageDate: "nope" });
    expect(await provider.findNearest(1, 2)).toBeNull();
  });

  it("aims the panorama and reports heading changes", async () => {
    const { pano } = installGoogle();
    const provider = createGoogleProvider("browser-key");
    const photo = (await provider.findNearest(1, 2))!;
    const headings: number[] = [];
    const container = document.createElement("div");
    const handle = await provider.mount({
      container, photo, heading: 40, reducedMotion: true, onHeading: (deg) => headings.push(deg),
    });
    expect(pano.setPov).toHaveBeenCalledWith({ heading: 40, pitch: 0 });
    expect(headings).toContain(40);
    pano.listeners.pov_changed();
    expect(headings).toContain(15);
    await handle.moveTo({ ...photo, lat: 3, lng: 4 }, 80);
    expect(pano.setPosition).toHaveBeenCalledWith({ lat: 3, lng: 4 });
    handle.destroy();
    expect(pano.setVisible).toHaveBeenCalledWith(false);
  });

  it("fails closed when the script cannot load, and the key stays out of the error", async () => {
    delete window.google;
    const pending = loadGoogleMaps("browser-key");
    const script = [...document.scripts].at(-1)!;
    expect(script.src).toContain("browser-key");
    script.onerror?.(new Event("error"));
    try {
      await pending;
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(StreetViewError);
      expect((err as Error).message).not.toContain("browser-key");
    }
    const again = loadGoogleMaps("browser-key");
    const next = [...document.scripts].at(-1)!;
    next.onload?.(new Event("load"));
    await expect(again).rejects.toBeInstanceOf(StreetViewError);
  });
});
