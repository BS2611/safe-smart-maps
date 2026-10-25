import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { BAND_TEXT } from "@/lib/format";
import { bandLayers, boundsOf, otherRoutesCollection, segmentCollection } from "@/lib/mapdata";
import { loadFixture } from "@/test-utils/fixtures";

import { MapLegend } from "./MapLegend";
import { RouteCard } from "./RouteCard";
import { RouteMap } from "./RouteMap";
import { SegmentMap } from "./SegmentMap";

const data = loadFixture();
const first = data.routes[0];

describe("SegmentMap", () => {
  it("draws one path per segment with its band, plus start and end", () => {
    const { container } = render(<SegmentMap routes={data.routes} selectedId={first.route_id} />);
    expect(container.querySelectorAll("path[data-band]")).toHaveLength(first.segments.length);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Route drawing: Most lit & active/);
    expect(screen.getByText("START")).toBeInTheDocument();
    expect(screen.getByText("END")).toBeInTheDocument();
  });

  it("does not rely on color alone: non-green bands get a dash pattern", () => {
    const { container } = render(<SegmentMap routes={data.routes} selectedId={first.route_id} />);
    const paths = [...container.querySelectorAll("path[data-band]")];
    const bands = new Set(paths.map((p) => p.getAttribute("data-band")));
    expect(bands.size).toBeGreaterThan(0);
    for (const p of paths) {
      if (p.getAttribute("data-band") !== "green") expect(p).toHaveAttribute("stroke-dasharray");
    }
  });

  it("emphasizes the chosen segment and falls back to the first route", () => {
    const { container } = render(<SegmentMap routes={data.routes} selectedId="missing" highlightSegment={0} />);
    const widths = [...container.querySelectorAll("path[data-band]")].map((p) => p.getAttribute("stroke-width"));
    expect(widths[0]).toBe("8");
    expect(widths[1]).toBe("5");
  });

  it("renders nothing without routes", () => {
    const { container } = render(<SegmentMap routes={[]} selectedId="x" />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("MapLegend", () => {
  it("names every band with text and a symbol", () => {
    render(<MapLegend />);
    for (const text of Object.values(BAND_TEXT)) expect(screen.getByText(text)).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
  });
});

describe("RouteMap", () => {
  it("falls back to the drawing and says why when there is no map key", () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "");
    render(<RouteMap routes={data.routes} selectedId={first.route_id} />);
    expect(screen.getByRole("img")).toBeInTheDocument();
    expect(screen.getByText(/Map tiles need a map key/)).toBeInTheDocument();
  });

  it("falls back to the drawing when the map library cannot start", async () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.fixture");
    vi.doMock("mapbox-gl", () => ({
      default: { Map: class { constructor() { throw new Error("no WebGL"); } } },
    }));
    vi.doMock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
    render(<RouteMap routes={data.routes} selectedId={first.route_id} />);
    expect(await screen.findByText(/The map could not load/)).toBeInTheDocument();
    expect(screen.getByRole("img")).toBeInTheDocument();
    vi.doUnmock("mapbox-gl");
  });

  it("renders nothing without routes", () => {
    const { container } = render(<RouteMap routes={[]} selectedId="x" />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("map data", () => {
  it("builds one feature per segment with its band", () => {
    const fc = segmentCollection(first);
    expect(fc.features).toHaveLength(first.segments.length);
    expect(fc.features[0].properties.band).toBe(first.segments[0].band);
    expect(fc.features[0].geometry.coordinates).toEqual([first.segments[0].start, first.segments[0].end]);
  });

  it("excludes the selected route from the faded layer", () => {
    const others = otherRoutesCollection(data.routes, first.route_id);
    expect(others.features.map((f) => f.properties.route_id)).not.toContain(first.route_id);
    expect(others.features).toHaveLength(data.routes.length - 1);
  });

  it("has one layer per band, with dashes everywhere except green", () => {
    const layers = bandLayers("sel");
    expect(layers.map((l) => l.id)).toEqual(["sel-green", "sel-yellow", "sel-red", "sel-unknown"]);
    expect(layers[0].paint).not.toHaveProperty("line-dasharray");
    for (const l of layers.slice(1)) expect(l.paint).toHaveProperty("line-dasharray");
  });

  it("computes bounds, or null with no routes", () => {
    const b = boundsOf(data.routes);
    expect(b?.[0][0]).toBeLessThan(b?.[1][0] as number);
    expect(boundsOf([])).toBeNull();
  });
});

describe("RouteCard", () => {
  const fastest = data.routes.find((r) => r.label === "fastest") ?? data.routes[data.routes.length - 1];
  const merged = data.routes.find((r) => r.also_labels.length > 0);

  it("shows the friendly name, never the API value, with the key numbers", () => {
    render(<RouteCard route={fastest} selected={false} onSelect={() => undefined} />);
    expect(screen.getByText("Fastest")).toBeInTheDocument();
    expect(screen.queryByText(/safest/i)).not.toBeInTheDocument();
    expect(screen.getByText("Coverage")).toBeInTheDocument();
    expect(screen.getByText("Longest empty stretch")).toBeInTheDocument();
    expect(screen.getByText("Open places")).toBeInTheDocument();
    expect(screen.getByText("Nearest help point")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute("href", `/routes/${fastest.route_id}`);
  });

  it("shows merged labels once and says so", () => {
    expect(merged).toBeDefined();
    render(<RouteCard route={merged!} selected onSelect={() => undefined} />);
    expect(screen.getByText(/are the same route/)).toBeInTheDocument();
    expect(screen.getByText("Balanced", { selector: ".badge" })).toBeInTheDocument();
  });

  it("marks the selected card and reports taps", async () => {
    const onSelect = vi.fn();
    render(<RouteCard route={fastest} selected onSelect={onSelect} />);
    const button = screen.getByRole("button", { name: /Fastest/ });
    expect(button).toHaveAttribute("aria-pressed", "true");
    await userEvent.setup().click(button);
    expect(onSelect).toHaveBeenCalled();
  });

  it("says not sure for missing numbers instead of showing zeros", () => {
    const unknown = {
      ...fastest, route_score: null, open_places_count: null, nearest_help_point: null,
      continuity: { ...fastest.continuity, coverage_pct: null, longest_gap_note: null },
    };
    render(<RouteCard route={unknown} selected={false} onSelect={() => undefined} />);
    expect(screen.getAllByText("Not sure").length).toBeGreaterThanOrEqual(4);
  });
});
