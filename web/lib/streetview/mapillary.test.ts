import { vi } from "vitest";

import { createMapillaryProvider, chooseMapillaryPhoto, parseMapillaryImages } from "./mapillary";
import { StreetViewError, type StreetViewPhoto } from "./types";

vi.mock("mapillary-js/dist/mapillary.css", () => ({}));

vi.mock("mapillary-js", () => {
  class Viewer {
    static instances: Viewer[] = [];
    opts: unknown;
    moveTo = vi.fn(async (id: string) => {
      if (id === "img-fail" || id === "nope") throw new Error("secret-token boom");
      return { id };
    });
    setCenter = vi.fn();
    setTransitionMode = vi.fn();
    getBearing = vi.fn(async () => 33);
    handlers = new Map<string, (event: { bearing: number }) => void>();
    on = vi.fn((type: string, cb: (event: { bearing: number }) => void) => { this.handlers.set(type, cb); });
    off = vi.fn();
    remove = vi.fn();
    resize = vi.fn();
    constructor(opts: unknown) {
      this.opts = opts;
      Viewer.instances.push(this);
    }
  }
  return { Viewer, TransitionMode: { Instantaneous: 1, Default: 0 } };
});

function photo(partial: Partial<StreetViewPhoto> & Pick<StreetViewPhoto, "id" | "lng" | "lat">): StreetViewPhoto {
  return { provider: "mapillary", compass: null, capturedAt: null, isPano: false, ...partial };
}

describe("Mapillary photos", () => {
  it("parses images and prefers a panorama", () => {
    const parsed = parseMapillaryImages({
      data: [
        { id: 1, geometry: { coordinates: [-122.1, 37.1] }, is_pano: false },
        { id: "2", computed_geometry: { coordinates: [-122.2, 37.2] }, compass_angle: 80, captured_at: 1_700_000_000_000, is_pano: true },
        { id: "", geometry: { coordinates: [0, 0] } },
        { nope: true },
        null,
        { id: "bad" },
      ],
    });
    expect(parsed).toHaveLength(2);
    expect(parsed[1].capturedAt).toMatch(/^2023-/);
    expect(parsed[1].compass).toBe(80);
    expect(chooseMapillaryPhoto(parsed, -122.1, 37.1)?.id).toBe("2");
    expect(chooseMapillaryPhoto([], 0, 0)).toBeNull();
    expect(parseMapillaryImages(null)).toEqual([]);
    expect(parseMapillaryImages({ data: "nope" })).toEqual([]);
    const closer = chooseMapillaryPhoto([
      photo({ id: "far", lng: 10, lat: 10, isPano: false }),
      photo({ id: "near", lng: 0.001, lat: 0, isPano: false }),
    ], 0, 0);
    expect(closer?.id).toBe("near");
  });

  it("asks Graph API with the token in a header, never in the address or an error", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      data: [{ id: "img", computed_geometry: { coordinates: [-122.4, 37.8] }, is_pano: true, compass_angle: 12 }],
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const provider = createMapillaryProvider("  secret-token  ");
    const hit = await provider.findNearest(-122.4, 37.8);
    expect(hit?.id).toBe("img");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [URL, RequestInit];
    expect(String(url)).not.toContain("secret-token");
    expect(String(url)).toContain("closeto=-122.4%2C37.8");
    expect((init.headers as { Authorization: string }).Authorization).toBe("OAuth secret-token");
    expect(provider.configured).toBe(true);
    expect(createMapillaryProvider("  ").configured).toBe(false);
  });

  it("turns a rejected token or a bad response into a street view error", async () => {
    const provider = createMapillaryProvider("secret-token");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("no", { status: 401 })));
    await expect(provider.findNearest(0, 0)).rejects.toMatchObject({ kind: "unavailable" });
    vi.stubGlobal("fetch", vi.fn(async () => new Response("no", { status: 500 })));
    await expect(provider.findNearest(0, 0)).rejects.toBeInstanceOf(StreetViewError);
    vi.stubGlobal("fetch", vi.fn(async () => new Response("not-json", { status: 200 })));
    await expect(provider.findNearest(0, 0)).rejects.toMatchObject({ kind: "failed" });
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("secret-token offline"); }));
    try {
      await provider.findNearest(0, 0);
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(StreetViewError);
      expect((err as Error).message).not.toContain("secret-token");
    }
    const ac = new AbortController();
    vi.stubGlobal("fetch", vi.fn(async () => {
      ac.abort();
      throw new DOMException("aborted", "AbortError");
    }));
    await expect(provider.findNearest(0, 0, ac.signal)).rejects.toThrow(/abort/i);
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ data: [] }), { status: 200 })));
    expect(await provider.findNearest(1, 2)).toBeNull();
  });

  it("mounts the viewer, looks along the walk, and removes it", async () => {
    const mod = await import("mapillary-js") as unknown as {
      Viewer: { instances: Array<{
        opts: { accessToken: string; imageId: string };
        moveTo: ReturnType<typeof vi.fn>;
        setCenter: ReturnType<typeof vi.fn>;
        setTransitionMode: ReturnType<typeof vi.fn>;
        getBearing: ReturnType<typeof vi.fn>;
        handlers: Map<string, (event: { bearing: number }) => void>;
        remove: ReturnType<typeof vi.fn>;
      }> };
    };
    const provider = createMapillaryProvider("secret-token");
    const container = document.createElement("div");
    const headings: number[] = [];
    const handle = await provider.mount({
      container,
      photo: photo({ id: "img", lng: -122.4, lat: 37.8, isPano: true, compass: 0 }),
      heading: 90,
      reducedMotion: true,
      onHeading: (deg) => headings.push(deg),
    });
    const viewer = mod.Viewer.instances.at(-1)!;
    expect(viewer.opts.accessToken).toBe("secret-token");
    expect(viewer.opts.imageId).toBe("img");
    expect(viewer.setTransitionMode).toHaveBeenCalledWith(1);
    expect(viewer.setCenter).toHaveBeenCalledWith([0.75, 0.5]);
    expect(headings).toContain(33);
    viewer.handlers.get("bearing")?.({ bearing: 120 });
    expect(headings).toContain(120);
    viewer.handlers.get("bearing")?.({ bearing: Number.NaN });
    await handle.moveTo(photo({ id: "next", lng: -122.4, lat: 37.81, isPano: false }), 10);
    expect(viewer.moveTo).toHaveBeenCalledWith("next");
    handle.destroy();
    expect(viewer.remove).toHaveBeenCalled();
  });

  it("reports a failed viewer without leaking the token", async () => {
    const mod = await import("mapillary-js") as unknown as {
      Viewer: { instances: Array<{ remove: ReturnType<typeof vi.fn> }> };
    };
    const provider = createMapillaryProvider("secret-token");
    const container = document.createElement("div");
    container.append("old");
    try {
      await provider.mount({
        container,
        photo: photo({ id: "img-fail", lng: 0, lat: 0, isPano: false }),
        heading: 0,
        reducedMotion: false,
        onHeading: () => undefined,
      });
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(StreetViewError);
      expect((err as Error).message).not.toContain("secret-token");
    }
    expect(mod.Viewer.instances.at(-1)?.remove).toHaveBeenCalled();
    expect(container.childNodes).toHaveLength(0);

    const handle = await provider.mount({
      container,
      photo: photo({ id: "ok", lng: 0, lat: 0, isPano: false }),
      heading: 0,
      reducedMotion: false,
      onHeading: () => undefined,
    });
    await expect(handle.moveTo(photo({ id: "nope", lng: 1, lat: 1 }), 0)).rejects.toMatchObject({ kind: "failed" });
    handle.destroy();
  });
});
