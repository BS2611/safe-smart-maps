import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { EMPTY_TRIP } from "@/lib/trip";
import { fixtureFor, READY_TRIP, renderWithTrip, stubFetch } from "@/test-utils/render";
import { rawFixture } from "@/test-utils/fixtures";
import { findBannedWording } from "@/lib/wording";

import { CheckingScreen, SourcesPanel } from "./CheckingScreen";
import { RoutesScreen } from "./RoutesScreen";

describe("CheckingScreen", () => {
  it("lists every check as 'Checking' with no fake percentages", () => {
    renderWithTrip(<CheckingScreen trip={READY_TRIP} onCancel={() => undefined} />, READY_TRIP);
    expect(screen.getAllByText("Checking")).toHaveLength(5);
    expect(screen.getByText(/cannot show a percentage/)).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.getByText(/Palace of Fine Arts/)).toBeInTheDocument();
  });

  it("can be cancelled", async () => {
    const onCancel = vi.fn();
    renderWithTrip(<CheckingScreen trip={READY_TRIP} onCancel={onCancel} />, READY_TRIP);
    await userEvent.setup().click(screen.getByRole("button", { name: /Cancel trip check/ }));
    expect(onCancel).toHaveBeenCalled();
  });
});

describe("SourcesPanel", () => {
  it("shows which sources were not available", () => {
    renderWithTrip(<SourcesPanel warnings={["Transit schedules are not configured, so transit shows as not sure."]} />);
    expect(screen.getByText("What we checked")).toBeInTheDocument();
    expect(screen.getByText("Not sure")).toBeInTheDocument();
    expect(screen.getAllByText("Done")).toHaveLength(4);
  });
});

describe("RoutesScreen", () => {
  it("asks for a trip when there is none", () => {
    renderWithTrip(<RoutesScreen />, EMPTY_TRIP);
    expect(screen.getByText("Choose a start and a destination first")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Plan a walk" })).toHaveAttribute("href", "/plan");
  });

  it("shows the checking screen, then the routes", async () => {
    const { calls } = stubFetch({ delayMs: 30 });
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    expect(screen.getByRole("heading", { name: "Checking your walk", level: 2 })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Why this route" })).toBeInTheDocument();
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toMatch(/\/v1\/routes$/);
    expect(calls[0].body?.depart_time).toBe("2026-10-25T03:00:00.000Z");
  });

  it("shows three route choices with friendly names, a fetched time and the legend", async () => {
    stubFetch();
    const { container } = renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    expect(screen.getByText("Most lit & active")).toBeInTheDocument();
    expect(screen.getByText("Fastest")).toBeInTheDocument();
    expect(screen.getByLabelText("When the data was fetched")).toHaveTextContent(/Fetched/);
    expect(screen.getByRole("list", { name: "Map legend" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare 8 PM vs 1 AM" })).toHaveAttribute("href", "/compare");
    expect(findBannedWording(container.textContent ?? "")).toEqual([]);
  });

  it("changes the explanation when another route is picked", async () => {
    stubFetch();
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    const why = screen.getByRole("heading", { name: "Why this route" }).closest("section, div") as HTMLElement;
    const before = within(why).getByText(/near an open place|not sure how active/).textContent;
    await userEvent.setup().click(screen.getByRole("button", { name: /^Fastest/ }));
    await waitFor(() => expect(within(why).getByText(/near an open place|not sure how active/).textContent).not.toBe(before));
    expect(screen.getByRole("button", { name: /^Fastest/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("lists the missing information from the server, including transit not configured", async () => {
    stubFetch();
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    expect(screen.getByText("Some information is missing")).toBeInTheDocument();
    expect(screen.getByText(/Transit schedules are not configured/)).toBeInTheDocument();
  });

  it("warns when the data is old", async () => {
    stubFetch({ respond: () => ({ ...(rawFixture() as object), data_fetched_at: "2020-01-01T00:00:00Z" }) });
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    expect(screen.getByText("This data is more than 2 hours old")).toBeInTheDocument();
  });

  it("says when AI wrote an explanation", async () => {
    stubFetch({
      respond: () => {
        const data = structuredClone(rawFixture()) as { routes: { explanation_source: string }[] };
        data.routes[0].explanation_source = "ai";
        return data;
      },
    });
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    expect(screen.getAllByText(/Explained by AI, may be wrong/).length).toBeGreaterThan(0);
  });

  it.each([
    ["NO_ROUTE", 404, /could not find a walking route/],
    ["NOT_CONFIGURED", 503, /not set up yet/],
    ["UPSTREAM_TIMEOUT", 504, /took too long/],
  ])("explains a %s error calmly and offers a retry", async (code, status, text) => {
    stubFetch({ status, respond: () => ({ error: { code, message: "server text" } }) });
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    expect(await screen.findByText("The check didn't finish")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(text);
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Change trip" })).toHaveAttribute("href", "/plan");
    expect(screen.getByText("In an emergency, call 911.")).toBeInTheDocument();
  });

  it("retries after an error and then shows the routes", async () => {
    let n = 0;
    stubFetch({
      respond: (_b) => (++n === 1 ? new Error("offline") : rawFixture()),
    });
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Why this route" })).toBeInTheDocument();
  });

  it("can be cancelled while checking", async () => {
    stubFetch({ delayMs: 500 });
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await userEvent.setup().click(await screen.findByRole("button", { name: /Cancel trip check/ }));
    expect(await screen.findByText("Check cancelled.")).toBeInTheDocument();
  });

  it("does not ask the server again for the same trip", async () => {
    const { calls } = stubFetch();
    const first = renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    await act(async () => { first.rerender(<></>); });
    expect(calls).toHaveLength(1);
  });

  it("shows the sample-data banner only in dev sample mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEV_FIXTURES", "1");
    const { calls } = stubFetch({ respond: (body) => fixtureFor(body?.depart_time) });
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    expect(screen.getByText("Sample data")).toBeInTheDocument();
    expect(calls[0].url).toContain("/dev-fixtures/");
  });

  it("does not show the sample-data banner or fixtures in normal use", async () => {
    stubFetch();
    renderWithTrip(<RoutesScreen />, READY_TRIP);
    await screen.findByRole("heading", { name: "Why this route" });
    expect(screen.queryByText("Sample data")).not.toBeInTheDocument();
  });
});
