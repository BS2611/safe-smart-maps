import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { loadFixture } from "@/test-utils/fixtures";
import { READY_TRIP, renderWithTrip } from "@/test-utils/render";

import { PreferencesGate } from "./PreferencesGate";
import { RouteMap } from "./RouteMap";
import { TripProvider, useTrip } from "./TripProvider";

const data = loadFixture();

describe("RouteMap with the map library (mocked, no WebGL here)", () => {
  it("adds the route layers once the map has loaded, then updates data when selection changes", async () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.fixture");
    const handlers: Record<string, () => void> = {};
    const sources = new Map<string, { setData: ReturnType<typeof vi.fn> }>();
    const layers: string[] = [];
    const remove = vi.fn();
    const fitBounds = vi.fn();
    class FakeMap {
      constructor(public options: Record<string, unknown>) { fakeInstances.push(this); }
      on(event: string, cb: () => void) { handlers[event] = cb; }
      addSource(id: string) { sources.set(id, { setData: vi.fn() }); }
      addLayer(layer: { id: string }) { layers.push(layer.id); }
      getSource(id: string) { return sources.get(id); }
      fitBounds = fitBounds;
      remove = remove;
    }
    const fakeInstances: FakeMap[] = [];
    vi.doMock("mapbox-gl", () => ({ default: { Map: FakeMap, accessToken: "" } }));
    vi.doMock("mapbox-gl/dist/mapbox-gl.css", () => ({}));

    const { rerender, unmount } = render(<RouteMap routes={data.routes} selectedId={data.routes[0].route_id} />);
    await waitFor(() => expect(fakeInstances).toHaveLength(1));
    expect(fakeInstances[0].options.style).toBe("mapbox://styles/mapbox/dark-v11");
    expect(screen.getByRole("region", { name: "Map of the selected route" })).toBeInTheDocument();

    await act(async () => { handlers.load(); });
    expect(layers).toEqual(expect.arrayContaining(["other-routes", "selected-route-green", "selected-route-red"]));
    expect(fitBounds).toHaveBeenCalled();

    const other = data.routes[data.routes.length - 1];
    rerender(<RouteMap routes={data.routes} selectedId={other.route_id} />);
    await waitFor(() => expect(sources.get("selected-route")?.setData).toHaveBeenCalled());

    unmount();
    expect(remove).toHaveBeenCalled();
    vi.doUnmock("mapbox-gl");
  });

  it("falls back to the drawing if the map reports an error", async () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.fixture");
    const handlers: Record<string, () => void> = {};
    class FakeMap {
      on(event: string, cb: () => void) { handlers[event] = cb; }
      remove() { /* nothing */ }
    }
    vi.doMock("mapbox-gl", () => ({ default: { Map: FakeMap, accessToken: "" } }));
    vi.doMock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
    render(<RouteMap routes={data.routes} selectedId={data.routes[0].route_id} />);
    await waitFor(() => expect(handlers.error).toBeDefined());
    await act(async () => { handlers.error(); });
    expect(await screen.findByText(/The map could not load/)).toBeInTheDocument();
    vi.doUnmock("mapbox-gl");
  });
});

describe("PreferencesGate", () => {
  it("renders the preferences screen with the default return page", async () => {
    renderWithTrip(<PreferencesGate />, READY_TRIP);
    expect(await screen.findByRole("heading", { name: "Route preferences" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back" })).toHaveAttribute("href", "/plan");
  });
});

describe("TripProvider", () => {
  function Probe() {
    const { trip, updateTrip, resetTrip, ready } = useTrip();
    return (
      <div>
        <span data-testid="ready">{String(ready)}</span>
        <span data-testid="from">{trip.from?.name ?? "none"}</span>
        <button onClick={() => updateTrip({ from: READY_TRIP.from })}>set</button>
        <button onClick={resetTrip}>reset</button>
      </div>
    );
  }

  it("loads a saved trip, saves changes and forgets everything on reset", async () => {
    window.sessionStorage.setItem("ssm.trip.v1", JSON.stringify(READY_TRIP));
    render(<TripProvider><Probe /></TripProvider>);
    await waitFor(() => expect(screen.getByTestId("ready")).toHaveTextContent("true"));
    expect(screen.getByTestId("from")).toHaveTextContent("Palace of Fine Arts");
    await userEvent.setup().click(screen.getByText("reset"));
    expect(screen.getByTestId("from")).toHaveTextContent("none");
    expect(window.sessionStorage.getItem("ssm.trip.v1")).toBeNull();
    await userEvent.setup().click(screen.getByText("set"));
    expect(window.sessionStorage.getItem("ssm.trip.v1")).toContain("Palace of Fine Arts");
  });

  it("refuses to be used outside the provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Probe />)).toThrow(/inside <TripProvider>/);
    spy.mockRestore();
  });
});

describe("RouteDetailGate", () => {
  it("reads the route id from the address and shows that route", async () => {
    const nav = await import("next/navigation");
    const spy = vi.spyOn(nav, "useSearchParams").mockReturnValue(new URLSearchParams("id=r-missing") as never);
    const { RouteDetailGate } = await import("./RouteDetailGate");
    const { stubFetch } = await import("@/test-utils/render");
    stubFetch();
    renderWithTrip(<RouteDetailGate />, READY_TRIP);
    expect(await screen.findByText("This route is not in your current results")).toBeInTheDocument();
    spy.mockRestore();
  });
});
