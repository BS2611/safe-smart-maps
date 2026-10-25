import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { EMPTY_TRIP, MAX_PRIORITIES } from "@/lib/trip";
import { renderWithTrip } from "@/test-utils/render";

import { push } from "../vitest.setup";
import { PreferencesScreen } from "./PreferencesScreen";

function savedSettings() {
  return JSON.parse(window.sessionStorage.getItem("ssm.trip.v1") as string).settings;
}

describe("PreferencesScreen", () => {
  it("starts from the defaults: 10 extra minutes, alone, nothing chosen", () => {
    renderWithTrip(<PreferencesScreen />, EMPTY_TRIP);
    expect(screen.getByText("Up to 10 extra min")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alone" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("0 / 2 selected")).toBeInTheDocument();
  });

  it("changes the extra minutes in steps of 5, and 0 reads as no extra time", () => {
    renderWithTrip(<PreferencesScreen />, EMPTY_TRIP);
    const slider = screen.getByRole("slider", { name: "Maximum extra minutes" });
    expect(slider).toHaveAttribute("step", "5");
    fireEvent.change(slider, { target: { value: "15" } });
    expect(screen.getByText("Up to 15 extra min")).toBeInTheDocument();
    fireEvent.change(slider, { target: { value: "0" } });
    expect(screen.getByText("No extra time")).toBeInTheDocument();
  });

  it("allows at most two priorities and disables the rest", async () => {
    renderWithTrip(<PreferencesScreen />, EMPTY_TRIP);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Lighting" }));
    await user.click(screen.getByRole("button", { name: "Open places" }));
    expect(screen.getByText(`${MAX_PRIORITIES} / ${MAX_PRIORITIES} selected`)).toBeInTheDocument();
    for (const name of ["Main roads", "Help points", "Transit"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
    await user.click(screen.getByRole("button", { name: /Lighting/ })); // deselect frees a slot
    expect(screen.getByRole("button", { name: "Transit" })).toBeEnabled();
  });

  it("applies the chosen settings and returns to where the user came from", async () => {
    renderWithTrip(<PreferencesScreen next="/routes" />, EMPTY_TRIP);
    const user = userEvent.setup();
    fireEvent.change(screen.getByRole("slider"), { target: { value: "20" } });
    await user.click(screen.getByRole("button", { name: "With someone" }));
    await user.click(screen.getByRole("button", { name: "Transit" }));
    await user.click(screen.getByRole("button", { name: "Apply preferences" }));
    expect(savedSettings()).toEqual({ maxExtraMinutes: 20, withCompanion: true, priorities: ["transit"] });
    expect(push).toHaveBeenCalledWith("/routes");
  });

  it("resets to the defaults without leaving the screen", async () => {
    renderWithTrip(<PreferencesScreen />, EMPTY_TRIP);
    const user = userEvent.setup();
    fireEvent.change(screen.getByRole("slider"), { target: { value: "20" } });
    await user.click(screen.getByRole("button", { name: "Reset to defaults" }));
    expect(screen.getByText("Up to 10 extra min")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("is honest about what the options do", () => {
    renderWithTrip(<PreferencesScreen />, EMPTY_TRIP);
    expect(screen.getByText(/does not change the street scores/)).toBeInTheDocument();
    expect(screen.getByText(/low weight \(5%\)/)).toBeInTheDocument();
    expect(screen.getByText(/recalculates your routes/)).toBeInTheDocument();
  });
});
