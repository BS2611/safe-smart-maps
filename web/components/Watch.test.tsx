import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { EMPTY_TRIP } from "@/lib/trip";
import { renderWithTrip } from "@/test-utils/render";

import { PreferencesScreen } from "./PreferencesScreen";
import { WatchScreen } from "./WatchScreen";

describe("WatchScreen", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("starts off: start is disabled and the pairing box is disabled with an honest note", () => {
    render(<WatchScreen />);
    expect(screen.getByRole("button", { name: "Off" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Start simulated reading" })).toBeDisabled();
    expect(screen.getByLabelText("Pairing code")).toBeDisabled();
    expect(screen.getByText(/watch app is not built yet/i)).toBeInTheDocument();
  });

  it("shows a Simulated badge on every reading and forgets readings on stop", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<WatchScreen />);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Start simulated reading" }));
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getByText(/Not a real reading/)).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(4000); });
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Stop and delete readings" }));
    expect(screen.queryByText("Simulated")).not.toBeInTheDocument();
    expect(screen.queryByText("bpm")).not.toBeInTheDocument();
  });

  it("turning the check off stops a running reading", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<WatchScreen />);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Start simulated reading" }));
    await user.click(screen.getByRole("button", { name: "Off" }));
    expect(screen.queryByText("bpm")).not.toBeInTheDocument();
  });

  it("stops the source when the screen closes and writes nothing to storage", async () => {
    const stop = vi.fn();
    const make = () => ({ start: (cb: (r: never) => void) => cb({ bpm: 80, ts: new Date().toISOString(), source: "simulated" } as never), stop });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { unmount } = render(<WatchScreen makeSource={make} />);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Start simulated reading" }));
    unmount();
    expect(stop).toHaveBeenCalled();
    expect(window.sessionStorage.length).toBe(0);
    expect(window.localStorage.length).toBe(0);
  });

  it("uses careful wording and points to 911", () => {
    render(<WatchScreen />);
    expect(screen.getByText(/not a medical tool/i)).toBeInTheDocument();
    expect(screen.getByText("In an emergency, call 911.")).toBeInTheDocument();
  });
});

describe("Preferences link to the watch check", () => {
  it("links to /watch", () => {
    renderWithTrip(<PreferencesScreen />, EMPTY_TRIP);
    expect(screen.getByRole("link", { name: "Open watch check" })).toHaveAttribute("href", "/watch");
  });
});
