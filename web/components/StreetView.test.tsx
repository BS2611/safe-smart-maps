import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { BAND_TEXT } from "@/lib/format";
import { darkestSegmentIndex, nearestIndex, nearestSegmentIndex, sampleRoute, segmentMidpoint } from "@/lib/streetview/geo";
import type { StreetViewPhoto, StreetViewProvider } from "@/lib/streetview/types";
import { loadFixture } from "@/test-utils/fixtures";
import { READY_TRIP, renderWithTrip, stubFetch } from "@/test-utils/render";
import { findBannedWording } from "@/lib/wording";

import { RouteDetailScreen } from "./RouteDetailScreen";
import { RouteMap } from "./RouteMap";
import { SegmentMap } from "./SegmentMap";
import { StreetView } from "./StreetView";

const data = loadFixture();
const route = data.routes[0];

function photoAt(lng: number, lat: number): StreetViewPhoto {
  return {
    provider: "mapillary", id: `${lng.toFixed(4)},${lat.toFixed(4)}`, lng, lat,
    compass: 0, capturedAt: "2026-10-01T18:00:00Z", isPano: true,
  };
}

function fakeProvider(overrides: Partial<StreetViewProvider> = {}) {
  const findNearest = vi.fn(async (lng: number, lat: number) => photoAt(lng, lat));
  const mount = vi.fn(async (args: { onHeading: (deg: number) => void; heading: number; reducedMotion: boolean }) => {
    args.onHeading(args.heading);
    return { moveTo: vi.fn(async () => undefined), destroy: vi.fn() };
  });
  const provider: StreetViewProvider = {
    id: "mapillary", configured: true, findNearest, mount, ...overrides,
  };
  return { provider, findNearest, mount };
}

describe("StreetView", () => {
  it("shows the stretch score and steps along the route", async () => {
    const user = userEvent.setup();
    const { provider, findNearest } = fakeProvider();
    const start = route.geometry.coordinates[0];
    const onClose = vi.fn();
    const onPosition = vi.fn();
    render(<StreetView route={route} provider={provider} onClose={onClose} onPosition={onPosition}
      entry={{ lng: start[0], lat: start[1], darkest: false }} />);
    const dialog = screen.getByRole("dialog", { name: "Street view" });
    const samples = sampleRoute(route.geometry.coordinates, 25);
    const seg = route.segments[nearestSegmentIndex(route.segments, samples[0][0], samples[0][1])];
    expect(within(dialog).getByText(`${BAND_TEXT[seg.band]} · ${Math.round(seg.score!)} / 100`)).toBeInTheDocument();
    expect(within(dialog).getByRole("list", { name: "Reasons for this stretch" }).children.length).toBeGreaterThan(0);
    expect(within(dialog).getByText(/Photos: Mapillary/)).toBeInTheDocument();
    expect(findBannedWording(dialog.textContent ?? "")).toEqual([]);
    await waitFor(() => expect(findNearest).toHaveBeenCalled());
    expect(await within(dialog).findByText("Drag the photo to look around.")).toBeInTheDocument();
    expect(within(dialog).getByRole("img", { name: /Mini map/ })).toHaveAccessibleName(/0 is north/);
    expect(within(dialog).getByRole("button", { name: "Back along the route" })).toBeDisabled();

    await user.click(within(dialog).getByRole("button", { name: "Forward along the route" }));
    await waitFor(() => expect(findNearest.mock.calls.length).toBeGreaterThan(1));
    const [firstLng, firstLat] = findNearest.mock.calls[0];
    const [nextLng, nextLat] = findNearest.mock.calls.at(-1)!;
    expect(nextLng !== firstLng || nextLat !== firstLat).toBe(true);
    expect(onPosition).toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: "Close street view" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("says street view is unavailable when no token is configured", async () => {
    const { provider, findNearest, mount } = fakeProvider({ configured: false });
    const start = route.geometry.coordinates[0];
    render(<StreetView route={route} provider={provider} onClose={() => undefined} onPosition={() => undefined}
      entry={{ lng: start[0], lat: start[1], darkest: false }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Street view is unavailable.");
    expect(screen.getByText(/The rest of this walk still works/)).toBeInTheDocument();
    expect(findNearest).not.toHaveBeenCalled();
    expect(mount).not.toHaveBeenCalled();
  });

  it("keeps the score when no photo is nearby or the viewer fails", async () => {
    const start = route.geometry.coordinates[0];
    const { provider: empty } = fakeProvider({ findNearest: vi.fn(async () => null) });
    const { unmount } = render(<StreetView route={route} provider={empty} onClose={() => undefined} onPosition={() => undefined}
      entry={{ lng: start[0], lat: start[1], darkest: false }} />);
    expect(await screen.findByText(/No street-level photo near this spot/)).toBeInTheDocument();
    expect(screen.getByText(/\/ 100/)).toBeInTheDocument();
    unmount();

    const { provider: broken } = fakeProvider({ mount: vi.fn(async () => { throw new Error("no webgl"); }) });
    render(<StreetView route={route} provider={broken} onClose={() => undefined} onPosition={() => undefined}
      entry={{ lng: start[0], lat: start[1], darkest: false }} />);
    expect(await screen.findByText("Street view could not load this spot.")).toBeInTheDocument();
  });

  it("labels the darkest stretch and moves with the arrow keys", async () => {
    const user = userEvent.setup();
    const { provider, findNearest } = fakeProvider();
    const onClose = vi.fn();
    const index = darkestSegmentIndex(route.segments)!;
    const [lng, lat] = segmentMidpoint(route.segments[index]);
    render(<StreetView route={route} provider={provider} onClose={onClose} onPosition={() => undefined}
      entry={{ lng, lat, darkest: true }} />);
    const samples = sampleRoute(route.geometry.coordinates, 25);
    const snapped = samples[nearestIndex(samples, lng, lat)];
    const at = nearestSegmentIndex(route.segments, snapped[0], snapped[1]);
    if (at === index) expect(screen.getByText("Darkest stretch on this route.")).toBeInTheDocument();
    await user.keyboard("{ArrowRight}");
    await waitFor(() => expect(findNearest.mock.calls.length).toBeGreaterThan(1));
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("passes reduced motion through to the viewer", async () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes("reduce"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    })) as unknown as typeof window.matchMedia;
    const { provider, mount } = fakeProvider();
    const start = route.geometry.coordinates[0];
    render(<StreetView route={route} provider={provider} onClose={() => undefined} onPosition={() => undefined}
      entry={{ lng: start[0], lat: start[1], darkest: false }} />);
    await waitFor(() => expect(mount).toHaveBeenCalled());
    expect(mount.mock.calls[0][0].reducedMotion).toBe(true);
  });
});

describe("street view on the route", () => {
  it("opens from a tapped stretch on the drawing and from the peg", async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    render(<SegmentMap routes={data.routes} selectedId={route.route_id} onPickPoint={onPick} />);
    expect(screen.getByRole("group", { name: /Route drawing/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Open street view on stretch 1,/ }));
    const [lng, lat] = segmentMidpoint(route.segments[0]);
    expect(onPick).toHaveBeenCalledWith(lng, lat);
    onPick.mockClear();
    await user.keyboard("{Enter}");
    expect(onPick).toHaveBeenCalled();
  });

  it("previews the darkest stretch and closes back to the route", async () => {
    vi.stubEnv("NEXT_PUBLIC_MAPILLARY_TOKEN", "");
    vi.stubEnv("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", "");
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "");
    stubFetch();
    const user = userEvent.setup();
    renderWithTrip(<RouteDetailScreen routeId={route.route_id} />, READY_TRIP);
    expect(await screen.findByRole("heading", { name: "Along the whole walk" })).toBeInTheDocument();
    expect(screen.getByText(/Tap the route, or drag the peg/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Preview the darkest stretch" }));
    const dialog = await screen.findByRole("dialog", { name: "Street view" });
    expect(within(dialog).getByText(/Street view is unavailable/)).toBeInTheDocument();
    expect(within(dialog).getByText(/\/ 100/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Close street view" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Along the whole walk" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to routes" })).toBeInTheDocument();
  });

  it("reports a map click and a peg drop", async () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.fixture");
    const handlers: Record<string, (event?: { lngLat?: { lng: number; lat: number } }) => void> = {};
    let button: HTMLButtonElement | null = null;
    let dragend: (() => void) | undefined;
    const setLngLat = vi.fn(function (this: { addTo: () => unknown }) { return this; });
    class FakeMap {
      constructor() { /* recorded by handlers */ }
      on(event: string, cb: (event?: { lngLat?: { lng: number; lat: number } }) => void) { handlers[event] = cb; }
      addSource() { /* unused */ }
      addLayer() { /* unused */ }
      getSource() { return { setData: vi.fn() }; }
      fitBounds() { /* unused */ }
      remove() { /* unused */ }
    }
    class Marker {
      constructor(opts: { element: HTMLButtonElement }) { button = opts.element; }
      setLngLat = setLngLat;
      addTo() { return this; }
      getLngLat() { return { lng: -122.41, lat: 37.79 }; }
      on(event: string, cb: () => void) { if (event === "dragend") dragend = cb; }
    }
    vi.doMock("mapbox-gl", () => ({ default: { Map: FakeMap, Marker, accessToken: "" } }));
    vi.doMock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
    const onPick = vi.fn();
    const { rerender } = render(<RouteMap routes={data.routes} selectedId={route.route_id} onPickPoint={onPick} />);
    await waitFor(() => expect(handlers.click).toBeTypeOf("function"));
    await act(async () => { handlers.click({ lngLat: { lng: -122.42, lat: 37.78 } }); });
    expect(onPick).toHaveBeenCalledWith(-122.42, 37.78);
    await waitFor(() => expect(button).not.toBeNull());
    button!.click();
    expect(onPick).toHaveBeenCalledWith(-122.41, 37.79);
    dragend?.();
    expect(onPick).toHaveBeenCalledTimes(3);
    rerender(<RouteMap routes={data.routes} selectedId={route.route_id} onPickPoint={onPick} pegman={{ lng: -122.2, lat: 37.5 }} />);
    await waitFor(() => expect(setLngLat).toHaveBeenCalledWith([-122.2, 37.5]));
    vi.doUnmock("mapbox-gl");
    vi.doUnmock("mapbox-gl/dist/mapbox-gl.css");
  });
});
