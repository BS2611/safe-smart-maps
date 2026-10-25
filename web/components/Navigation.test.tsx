import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import * as checkin from "@/lib/nav/checkin";
import * as sensors from "@/lib/nav/sensors";
import { DEFAULT_SETTINGS } from "@/lib/trip";
import type { Route } from "@/lib/types";
import { findBannedWording } from "@/lib/wording";
import { loadFixture } from "@/test-utils/fixtures";
import { READY_TRIP, renderWithTrip } from "@/test-utils/render";

import { NavigationScreen } from "./NavigationScreen";

const route = loadFixture().routes[0];

function withStartScore(startScore: number, otherScore: number): Route {
  const start = route.geometry.coordinates[0] as [number, number];
  return {
    ...route,
    segments: route.segments.map((seg, i) => i === 0
      ? { ...seg, score: startScore, start, end: start }
      : { ...seg, score: otherScore }),
  };
}

describe("NavigationScreen", () => {
  it("shows the next maneuver and a labeled simulated walk", async () => {
    const user = userEvent.setup();
    const { container } = renderWithTrip(
      <NavigationScreen route={route} onClose={() => {}} onReroute={() => {}} />,
    );
    expect(await screen.findByRole("region", { name: "Next maneuver" })).toBeInTheDocument();
    expect(screen.getByText("Street name: not sure")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Simulate walk" }));
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop simulation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "North up" })).toHaveAttribute("aria-pressed", "false");
    expect(findBannedWording(container.textContent ?? "")).toEqual([]);
  });

  it("opens street view at the current point, toggles heading, and ends", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithTrip(<NavigationScreen route={route} onClose={onClose} onReroute={() => {}} />);
    await user.click(await screen.findByRole("button", { name: "Street view" }));
    expect(await screen.findByText(/Street view is unavailable/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close street view" }));
    await user.click(screen.getByRole("button", { name: "North up" }));
    expect(screen.getByRole("button", { name: /North up|Heading up/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Vibrate on" }));
    expect(screen.getByRole("button", { name: "Vibrate off" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "End" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("stays quiet when watch check-in is off", async () => {
    renderWithTrip(
      <NavigationScreen route={withStartScore(5, 90)} onClose={() => {}} onReroute={() => {}} checkInIntervalMs={30} />,
      READY_TRIP,
    );
    await screen.findByRole("region", { name: "Next maneuver" });
    await new Promise((r) => setTimeout(r, 80));
    expect(screen.queryByRole("status", { name: "Watch check-in" })).not.toBeInTheDocument();
  });

  it("checks in on the darkest stretch, buzzes, and clears on I'm OK", async () => {
    const ping = vi.spyOn(checkin, "pingPairedWatch");
    const buzz = vi.spyOn(sensors, "buzz").mockResolvedValue(undefined);
    const user = userEvent.setup();
    const trip = { ...READY_TRIP, settings: { ...DEFAULT_SETTINGS, watchCheckIn: true } };
    renderWithTrip(
      <NavigationScreen route={withStartScore(5, 90)} onClose={() => {}} onReroute={() => {}} checkInIntervalMs={60_000} />,
      trip,
    );
    expect(await screen.findByRole("status", { name: "Watch check-in" })).toHaveTextContent("Darkest stretch");
    expect(ping).toHaveBeenCalledWith("darkest");
    expect(buzz).toHaveBeenCalledWith(true);
    expect(screen.getByText(/does not guarantee safety/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "I'm OK" }));
    await waitFor(() => expect(screen.queryByRole("status", { name: "Watch check-in" })).not.toBeInTheDocument());
    await new Promise((r) => setTimeout(r, 40));
    expect(screen.queryByRole("status", { name: "Watch check-in" })).not.toBeInTheDocument();
  });

  it("checks in again after the interval", async () => {
    const ping = vi.spyOn(checkin, "pingPairedWatch");
    const user = userEvent.setup();
    const trip = { ...READY_TRIP, settings: { ...DEFAULT_SETTINGS, watchCheckIn: true } };
    renderWithTrip(
      <NavigationScreen route={withStartScore(90, 10)} onClose={() => {}} onReroute={() => {}} checkInIntervalMs={40} />,
      trip,
    );
    expect(await screen.findByRole("status", { name: "Watch check-in" })).toHaveTextContent("A few minutes have passed");
    expect(ping).toHaveBeenCalledWith("interval");
    await user.click(screen.getByRole("button", { name: "I'm OK" }));
    expect(await screen.findByRole("status", { name: "Watch check-in" })).toBeInTheDocument();
  });
});
