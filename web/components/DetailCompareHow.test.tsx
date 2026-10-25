import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FACTORS } from "@/lib/scoring-info";
import { EMPTY_TRIP } from "@/lib/trip";
import { loadFixture } from "@/test-utils/fixtures";
import { fixtureFor, READY_TRIP, renderWithTrip, stubFetch } from "@/test-utils/render";
import { findBannedWording } from "@/lib/wording";

import { push } from "../vitest.setup";
import { CompareScreen } from "./CompareScreen";
import { HowScoresScreen } from "./HowScoresScreen";
import { RouteDetailScreen } from "./RouteDetailScreen";

const data = loadFixture();
const route = data.routes[0];

describe("RouteDetailScreen", () => {
  it("shows the continuity numbers for the whole walk", async () => {
    stubFetch();
    renderWithTrip(<RouteDetailScreen routeId={route.route_id} />, READY_TRIP);
    expect(await screen.findByRole("heading", { name: "Along the whole walk" })).toBeInTheDocument();
    expect(screen.getByText("Coverage")).toBeInTheDocument();
    expect(screen.getByText("Longest empty stretch")).toBeInTheDocument();
    expect(screen.getByText(/Lowest 200 m stretch/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /target 80%/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Most lit & active" })).toBeInTheDocument();
  });

  it("lists all eight factors with their weights, activity labeled an estimate", async () => {
    stubFetch();
    renderWithTrip(<RouteDetailScreen routeId={route.route_id} />, READY_TRIP);
    const section = (await screen.findByRole("heading", { name: "What we checked" })).closest("section") as HTMLElement;
    for (const f of FACTORS) expect(within(section).getByText(f.label, { exact: false })).toBeInTheDocument();
    expect(screen.getAllByText(/% of score/)).toHaveLength(8);
    expect(within(section).getByText("Estimate")).toBeInTheDocument();
    expect(within(section).getByText(/Running transit/).parentElement).toHaveTextContent("Not sure");
  });

  it("shows the reasons for a stretch the user taps, and hides them on a second tap", async () => {
    stubFetch();
    renderWithTrip(<RouteDetailScreen routeId={route.route_id} />, READY_TRIP);
    const strip = await screen.findByRole("group", { name: "Route segments" });
    const user = userEvent.setup();
    const first = within(strip).getAllByRole("button")[0];
    await user.click(first);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(/You reach this part at about/);
    expect(within(status).getByRole("list", { name: "Reasons" }).children.length).toBeGreaterThan(0);
    await user.click(first);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("every stretch has text, not only color", async () => {
    stubFetch();
    renderWithTrip(<RouteDetailScreen routeId={route.route_id} />, READY_TRIP);
    const strip = await screen.findByRole("group", { name: "Route segments" });
    for (const b of within(strip).getAllByRole("button")) {
      expect(b).toHaveAccessibleName(/Stretch \d+: (Better lit & active|Mixed|Fewer supports|Not sure)/);
    }
  });

  it("explains the route in words and never says safe", async () => {
    stubFetch();
    const { container } = renderWithTrip(<RouteDetailScreen routeId={route.route_id} />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    expect(screen.getByText(route.explanation)).toBeInTheDocument();
    expect(findBannedWording(container.textContent ?? "")).toEqual([]);
  });

  it("handles a route that is not in the current results", async () => {
    stubFetch();
    renderWithTrip(<RouteDetailScreen routeId="r-missing" />, READY_TRIP);
    expect(await screen.findByText("This route is not in your current results")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to routes" })).toHaveAttribute("href", "/routes");
  });

  it("handles errors and an empty trip", async () => {
    stubFetch({ status: 502, respond: () => ({ error: { code: "UPSTREAM_ERROR", message: "x" } }) });
    renderWithTrip(<RouteDetailScreen routeId="x" />, READY_TRIP);
    expect(await screen.findByText("This route didn't load")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("asks for a trip when there is none", async () => {
    renderWithTrip(<RouteDetailScreen routeId="x" />, EMPTY_TRIP);
    expect(await screen.findByText(/Your trip is empty/)).toBeInTheDocument();
  });
});

describe("CompareScreen", () => {
  const NOW = new Date("2026-10-24T22:30:00Z");
  const tripBoth = READY_TRIP;

  function stubBoth() {
    return stubFetch({ respond: (body) => fixtureFor(body?.depart_time) });
  }

  it("asks for a trip when there is none", () => {
    renderWithTrip(<CompareScreen now={NOW} />, EMPTY_TRIP);
    expect(screen.getByText("Choose a start and a destination first")).toBeInTheDocument();
  });

  it("checks 8 PM and 1 AM tonight (two requests) and compares them", async () => {
    const { calls } = stubBoth();
    renderWithTrip(<CompareScreen now={NOW} />, tripBoth);
    expect(await screen.findByRole("heading", { name: /Key difference at 1:00 AM/ })).toBeInTheDocument();
    const times = calls.map((c) => c.body?.depart_time).sort();
    expect(times).toEqual(["2026-10-25T03:00:00.000Z", "2026-10-25T08:00:00.000Z"]);
  });

  it("shows the coverage change in the key difference box and the table", async () => {
    stubBoth();
    renderWithTrip(<CompareScreen now={NOW} />, tripBoth);
    await screen.findByRole("heading", { name: /Key difference/ });
    expect(screen.getByText(/Coverage drops from \d+% to \d+%/)).toBeInTheDocument();
    const table = screen.getByRole("table");
    for (const row of ["Primary route", "Walk duration", "Coverage", "Longest gap", "Open places", "Lowest 200 m"]) {
      expect(within(table).getByText(row, { exact: false })).toBeInTheDocument();
    }
    expect(screen.getByRole("columnheader", { name: "1 AM" })).toBeInTheDocument();
  });

  it("switches the map between the two times", async () => {
    stubBoth();
    renderWithTrip(<CompareScreen now={NOW} />, tripBoth);
    await screen.findByRole("heading", { name: /Key difference/ });
    const tabs = screen.getByRole("group", { name: "Departure time" });
    const [eight, one] = within(tabs).getAllByRole("button");
    expect(eight).toHaveAttribute("aria-pressed", "true");
    await userEvent.setup().click(one);
    expect(one).toHaveAttribute("aria-pressed", "true");
  });

  it("lets the user choose either departure time and go to the routes", async () => {
    stubBoth();
    renderWithTrip(<CompareScreen now={NOW} />, tripBoth);
    await screen.findByRole("heading", { name: /Key difference/ });
    await userEvent.setup().click(screen.getByRole("button", { name: "Use 1:00 AM departure" }));
    expect(JSON.parse(window.sessionStorage.getItem("ssm.trip.v1") as string).departISO).toBe("2026-10-25T08:00:00.000Z");
    expect(push).toHaveBeenCalledWith("/routes");
    await userEvent.setup().click(screen.getByRole("button", { name: "Use 8:00 PM departure" }));
    expect(push).toHaveBeenLastCalledWith("/routes");
  });

  it("shows an error if either check fails", async () => {
    stubFetch({ respond: (body) => (body?.depart_time.startsWith("2026-10-25T08") ? new Error("offline") : fixtureFor(body?.depart_time)) });
    renderWithTrip(<CompareScreen now={NOW} />, tripBoth);
    expect(await screen.findByText("The comparison didn't finish")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Try again" }));
  });

  it("is labeled with the time zone and never says safe", async () => {
    stubBoth();
    const { container } = renderWithTrip(<CompareScreen now={NOW} />, tripBoth);
    await screen.findByRole("heading", { name: /Key difference/ });
    expect(screen.getByText(/Los Angeles time zone/)).toBeInTheDocument();
    expect(findBannedWording(container.textContent ?? "")).toEqual([]);
    await waitFor(() => expect(screen.queryByText("Sample data")).not.toBeInTheDocument());
  });
});

describe("HowScoresScreen", () => {
  it("lists the eight checks with weights that total 100%", () => {
    renderWithTrip(<HowScoresScreen />);
    expect(screen.getByText("100% total")).toBeInTheDocument();
    for (const f of FACTORS) expect(screen.getByRole("heading", { name: new RegExp(f.label) })).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
  });

  it("explains the whole-route rule and shows the formula", () => {
    renderWithTrip(<HowScoresScreen />);
    expect(screen.getByRole("heading", { name: "2. The whole route matters" })).toBeInTheDocument();
    expect(screen.getByText(/Route score = 50%/)).toBeInTheDocument();
    expect(screen.getByText(/Anything over 150 m/)).toBeInTheDocument();
  });

  it("is honest about sources, limits and privacy, and offers 911", () => {
    const { container } = renderWithTrip(<HowScoresScreen />);
    expect(screen.getByText(/Transit:/).parentElement).toHaveTextContent(/not connected yet/);
    expect(screen.getByText(/AI can be wrong/)).toBeInTheDocument();
    expect(screen.getByText(/Incident data can be unfair/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Call 911" })).toHaveAttribute("href", "tel:911");
    expect(findBannedWording(container.textContent ?? "")).toEqual([]);
  });

  it("returns to where it was opened from", () => {
    renderWithTrip(<HowScoresScreen backHref="/plan" />);
    expect(screen.getByRole("link", { name: "Return" })).toHaveAttribute("href", "/plan");
  });
});
