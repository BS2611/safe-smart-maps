import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { findBannedWording } from "@/lib/wording";
import { loadFixture } from "@/test-utils/fixtures";
import { renderWithTrip } from "@/test-utils/render";

import { NavigationScreen } from "./NavigationScreen";

const route = loadFixture().routes[0];

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
});
