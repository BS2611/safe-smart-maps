import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import * as geocode from "@/lib/geocode";
import { DEMO_PLACES } from "@/lib/places";
import { EMPTY_TRIP } from "@/lib/trip";
import { READY_TRIP, renderWithTrip } from "@/test-utils/render";

import { push } from "../vitest.setup";
import { DepartureField } from "./DepartureField";
import { PlaceField } from "./PlaceField";
import { PlanTripScreen } from "./PlanTripScreen";

const SATURDAY_3PM = new Date("2026-10-24T22:30:00Z");

describe("DepartureField", () => {
  it("offers now, 8 PM, 1 AM and a custom time", async () => {
    const onChange = vi.fn();
    render(<DepartureField value={null} onChange={onChange} now={SATURDAY_3PM} />);
    const user = userEvent.setup();
    expect(screen.getByRole("button", { name: "Now" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "8 PM" }));
    expect(onChange).toHaveBeenLastCalledWith("2026-10-25T03:00:00.000Z");
    await user.click(screen.getByRole("button", { name: "1 AM" }));
    expect(onChange).toHaveBeenLastCalledWith("2026-10-25T08:00:00.000Z");
    await user.click(screen.getByRole("button", { name: "Now" }));
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("explains that scores use the arrival time", () => {
    render(<DepartureField value="2026-10-25T03:00:00.000Z" onChange={() => undefined} now={SATURDAY_3PM} />);
    expect(screen.getByRole("button", { name: "8 PM" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Scores follow when you reach each street/)).toBeInTheDocument();
    expect(screen.getByText(/Sat 8:00 PM \(San Francisco time\)/)).toBeInTheDocument();
  });

  it("lets the user pick a time, read as San Francisco time", async () => {
    const onChange = vi.fn();
    render(<DepartureField value="2026-10-25T03:00:00.000Z" onChange={onChange} now={SATURDAY_3PM} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Custom" }));
    const input = screen.getByLabelText(/Departure time/);
    fireEvent.change(input, { target: { value: "2026-10-24T23:15" } });
    expect(onChange).toHaveBeenLastCalledWith("2026-10-25T06:15:00.000Z");
    fireEvent.change(input, { target: { value: "" } }); // cleared: ignored
    expect(onChange).toHaveBeenCalledTimes(2);
  });
});

describe("PlaceField", () => {
  const base = { label: "From", presets: DEMO_PLACES, onChange: vi.fn() };

  it("selects a demo place with one tap", async () => {
    const onChange = vi.fn();
    render(<PlaceField {...base} onChange={onChange} value={null} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Palace of Fine Arts" }));
    expect(onChange).toHaveBeenCalledWith(DEMO_PLACES[0]);
  });

  it("says address search needs a key when none is set", () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "");
    render(<PlaceField {...base} value={null} />);
    expect(screen.getByText(/Address search needs a map key/)).toBeInTheDocument();
  });

  it("clears the chosen place when the user edits the text", async () => {
    const onChange = vi.fn();
    render(<PlaceField {...base} onChange={onChange} value={DEMO_PLACES[0]} />);
    expect(screen.getByLabelText("From")).toHaveValue("Palace of Fine Arts");
    await userEvent.setup().type(screen.getByLabelText("From"), "x");
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("shows search suggestions and picks one", async () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.fixture");
    const found = { id: "1", name: "Fixture Cafe, San Francisco", lat: 37.8, lng: -122.4 };
    vi.spyOn(geocode, "searchPlaces").mockResolvedValue([found]);
    const onChange = vi.fn();
    render(<PlaceField {...base} onChange={onChange} value={null} />);
    await userEvent.setup().type(screen.getByLabelText("From"), "fixture");
    const option = await screen.findByRole("button", { name: found.name }, { timeout: 2000 });
    await userEvent.setup().click(option);
    expect(onChange).toHaveBeenCalledWith(found);
    vi.restoreAllMocks();
  });

  it("tells the user when search finds nothing or fails", async () => {
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.fixture");
    const spy = vi.spyOn(geocode, "searchPlaces").mockResolvedValueOnce([]);
    render(<PlaceField {...base} value={null} />);
    await userEvent.setup().type(screen.getByLabelText("From"), "nowhere");
    expect(await screen.findByText(/No matches/, undefined, { timeout: 2000 })).toBeInTheDocument();
    spy.mockRejectedValue(new Error("down"));
    await userEvent.setup().type(screen.getByLabelText("From"), "z");
    expect(await screen.findByText(/Search is not available right now/, undefined, { timeout: 2000 })).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  describe("use my location", () => {
    function stubGeo(impl: ((ok: PositionCallback, err: PositionErrorCallback) => void) | null) {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true, value: impl ? { getCurrentPosition: impl } : undefined,
      });
    }

    it("uses the position when allowed", async () => {
      stubGeo((ok) => ok({ coords: { latitude: 37.79, longitude: -122.41 } } as GeolocationPosition));
      const onChange = vi.fn();
      render(<PlaceField {...base} onChange={onChange} value={null} allowMyLocation />);
      await userEvent.setup().click(screen.getByRole("button", { name: /Use my location/ }));
      expect(onChange).toHaveBeenCalledWith({ id: "my-location", name: "My location", lat: 37.79, lng: -122.41 });
    });

    it("asks for a starting point when location is denied", async () => {
      stubGeo((_ok, err) => err({ code: 1 } as GeolocationPositionError));
      const denied = vi.fn();
      render(<PlaceField {...base} value={null} allowMyLocation onLocationDenied={denied} />);
      await userEvent.setup().click(screen.getByRole("button", { name: /Use my location/ }));
      expect(screen.getByText("Location is off. Enter a starting point.")).toBeInTheDocument();
      expect(denied).toHaveBeenCalled();
    });

    it("handles browsers without geolocation", async () => {
      stubGeo(null);
      render(<PlaceField {...base} value={null} allowMyLocation />);
      await userEvent.setup().click(screen.getByRole("button", { name: /Use my location/ }));
      expect(screen.getByText(/Location is not available/)).toBeInTheDocument();
    });
  });
});

describe("PlanTripScreen", () => {
  it("keeps Show routes disabled until there are two different places", () => {
    renderWithTrip(<PlanTripScreen />, EMPTY_TRIP);
    expect(screen.getByRole("button", { name: "Show routes" })).toBeDisabled();
  });

  it("goes to the routes screen and fixes 'leave now' to a real time", async () => {
    renderWithTrip(<PlanTripScreen />, { ...READY_TRIP, departISO: null });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Show routes" }));
    expect(push).toHaveBeenCalledWith("/routes");
    expect(JSON.parse(window.sessionStorage.getItem("ssm.trip.v1") as string).departISO).toMatch(/Z$/);
  });

  it("swaps start and destination", async () => {
    renderWithTrip(<PlanTripScreen />, READY_TRIP);
    await userEvent.setup().click(screen.getByRole("button", { name: "Swap start and destination" }));
    await waitFor(() => expect(screen.getByLabelText("From")).toHaveValue(DEMO_PLACES[1].name));
    expect(screen.getByLabelText("To")).toHaveValue(DEMO_PLACES[0].name);
  });

  it("links to preferences and explains the demo area", () => {
    renderWithTrip(<PlanTripScreen />, READY_TRIP);
    expect(screen.getByRole("link", { name: "Route preferences" })).toHaveAttribute("href", "/preferences");
    expect(screen.getByText(/Live data covers the demo area/)).toBeInTheDocument();
  });

  it("rebuilds the from/to fields when a trip is loaded from session storage", async () => {
    window.sessionStorage.setItem("ssm.trip.v1", JSON.stringify(READY_TRIP));
    const { TripProvider } = await import("./TripProvider");
    await act(async () => { render(<TripProvider><PlanTripScreen /></TripProvider>); });
    expect(screen.getByLabelText("To")).toHaveValue(DEMO_PLACES[1].name);
  });
});
