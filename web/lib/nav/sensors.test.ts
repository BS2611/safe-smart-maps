import { buzz, watchCompass, watchLocation } from "./sensors";

const native = vi.hoisted(() => ({ value: false }));

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: () => native.value },
}));

const geo = vi.hoisted(() => ({
  requestPermissions: vi.fn(),
  watchPosition: vi.fn(),
  clearWatch: vi.fn(),
}));

vi.mock("@capacitor/geolocation", () => ({ Geolocation: geo }));

const haptics = vi.hoisted(() => ({ impact: vi.fn() }));
vi.mock("@capacitor/haptics", () => ({
  Haptics: haptics,
  ImpactStyle: { Medium: "MEDIUM" },
}));

const motion = vi.hoisted(() => ({ addListener: vi.fn() }));
vi.mock("@capacitor/motion", () => ({ Motion: motion }));

describe("location and compass sensors", () => {
  afterEach(() => {
    native.value = false;
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("watches the browser position and reports a denial", async () => {
    const fixes: unknown[] = [];
    const statuses: string[] = [];
    const slot: {
      watch: ((pos: GeolocationPosition) => void) | null;
      fail: ((err: { code: number }) => void) | null;
    } = { watch: null, fail: null };
    const clearWatch = vi.fn();
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        watchPosition: (ok: (pos: GeolocationPosition) => void, err: (error: { code: number }) => void) => {
          slot.watch = ok;
          slot.fail = err;
          return 7;
        },
        clearWatch,
      },
    });
    const handle = await watchLocation((fix) => fixes.push(fix), (status) => statuses.push(status));
    slot.watch?.({
      coords: { longitude: -122.4, latitude: 37.8, accuracy: 5, heading: 12 },
    } as GeolocationPosition);
    expect(fixes).toEqual([{ lng: -122.4, lat: 37.8, accuracyM: 5, course: 12 }]);
    expect(statuses).toContain("live");
    slot.fail?.({ code: 1 });
    expect(statuses).toContain("denied");
    slot.fail?.({ code: 2 });
    expect(statuses).toContain("unavailable");
    handle.stop();
    expect(clearWatch).toHaveBeenCalledWith(7);
  });

  it("says location is unavailable when the browser has no geolocation", async () => {
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: undefined });
    const statuses: string[] = [];
    await watchLocation(() => undefined, (status) => statuses.push(status));
    expect(statuses).toEqual(["unavailable"]);
  });

  it("uses Capacitor geolocation on Android and stops when permission is denied", async () => {
    native.value = true;
    geo.requestPermissions.mockResolvedValueOnce({ location: "denied", coarseLocation: "denied" });
    const statuses: string[] = [];
    const denied = await watchLocation(() => undefined, (status) => statuses.push(status));
    expect(statuses).toEqual(["denied"]);
    denied.stop();

    geo.requestPermissions.mockResolvedValueOnce({ location: "granted", coarseLocation: "granted" });
    const slot: { callback: ((pos: { coords: { longitude: number; latitude: number; accuracy: number; heading: number | null; trueHeading: number | null } } | null, err?: unknown) => void) | null } = { callback: null };
    geo.watchPosition.mockImplementationOnce(async (_opts: unknown, cb: NonNullable<typeof slot.callback>) => {
      slot.callback = cb;
      return "watch-1";
    });
    const fixes: unknown[] = [];
    const handle = await watchLocation((fix) => fixes.push(fix), (status) => statuses.push(status));
    slot.callback?.({
      coords: { longitude: -122.4, latitude: 37.8, accuracy: 4, heading: 90, trueHeading: 80 },
    }, undefined);
    slot.callback?.(null, new Error("skip"));
    expect(fixes).toEqual([{ lng: -122.4, lat: 37.8, accuracyM: 4, course: 80 }]);
    handle.stop();
    expect(geo.clearWatch).toHaveBeenCalledWith({ id: "watch-1" });
  });

  it("asks iOS for compass permission and reads an orientation event", async () => {
    const remove = vi.fn();
    motion.addListener.mockImplementationOnce(async (_name: string, cb: (event: unknown) => void) => {
      cb({ alpha: 90, absolute: true });
      return { remove };
    });
    const headings: Array<number | null> = [];
    const handle = await watchCompass((deg) => headings.push(deg));
    expect(handle.status).toBe("on");
    expect(headings).toEqual([270]);
    handle.stop();
    expect(remove).toHaveBeenCalled();
  });

  it("treats a failed compass prompt as denied and falls back if motion is missing", async () => {
    vi.stubGlobal("DeviceOrientationEvent", {
      requestPermission: async () => { throw new Error("blocked"); },
    });
    const denied = await watchCompass(() => undefined);
    expect(denied.status).toBe("denied");

    vi.unstubAllGlobals();
    vi.stubGlobal("DeviceOrientationEvent", function DeviceOrientationEvent() { return undefined; });
    motion.addListener.mockRejectedValueOnce(new Error("missing"));
    const headings: Array<number | null> = [];
    const handle = await watchCompass((deg) => headings.push(deg));
    expect(handle.status).toBe("on");
    window.dispatchEvent(new Event("deviceorientation"));
    handle.stop();
  });

  it("stops when the iOS compass prompt is denied", async () => {
    const requestPermission = vi.fn(async () => "denied");
    vi.stubGlobal("DeviceOrientationEvent", { requestPermission });
    const handle = await watchCompass(() => undefined);
    expect(handle.status).toBe("denied");
    handle.stop();
  });

  it("vibrates on the web, and stays quiet when reduced motion is on", async () => {
    const vibrate = vi.fn();
    Object.defineProperty(navigator, "vibrate", { configurable: true, value: vibrate });
    window.matchMedia = (() => ({ matches: false })) as unknown as typeof window.matchMedia;
    await buzz(true);
    expect(vibrate).toHaveBeenCalledWith(24);
    await buzz(false);
    expect(vibrate).toHaveBeenCalledTimes(1);

    window.matchMedia = (() => ({ matches: true })) as unknown as typeof window.matchMedia;
    await buzz(true);
    expect(vibrate).toHaveBeenCalledTimes(1);

    native.value = true;
    window.matchMedia = (() => ({ matches: false })) as unknown as typeof window.matchMedia;
    await buzz(true);
    expect(haptics.impact).toHaveBeenCalled();
  });
});
