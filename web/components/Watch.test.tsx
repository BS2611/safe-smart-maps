import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { EMPTY_TRIP } from "@/lib/trip";
import { fakeRelay } from "@/test-utils/fakeRelay";
import { renderWithTrip } from "@/test-utils/render";

import { PreferencesScreen } from "./PreferencesScreen";
import { WatchScreen } from "./WatchScreen";

const setup = () => {
  const r = fakeRelay();
  const ui = <WatchScreen relay={{ baseUrl: "http://api.test", fetchImpl: r.impl, pollMs: 1000 }} />;
  return { r, ui };
};
const tick = (ms: number) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });

describe("WatchScreen", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("starts off: nothing can start until the user opts in", () => {
    render(setup().ui);
    expect(screen.getByRole("button", { name: "Off" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Get pairing code" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Start simulated reading" })).toBeDisabled();
    expect(screen.getByText("Not connected.")).toBeInTheDocument();
  });

  it("shows a Simulated badge on simulated readings and forgets them on stop", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(setup().ui);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Start simulated reading" }));
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getByText(/Not a real reading/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Stop and delete readings" }));
    expect(screen.queryByText("Simulated")).not.toBeInTheDocument();
    expect(screen.queryByText("bpm")).not.toBeInTheDocument();
  });

  it("turning the check off stops a running simulated reading", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(setup().ui);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Start simulated reading" }));
    await user.click(screen.getByRole("button", { name: "Off" }));
    expect(screen.queryByText("bpm")).not.toBeInTheDocument();
  });

  it("pairs: shows the code, then Connected, then live watch readings without a Simulated badge", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { r, ui } = setup();
    render(ui);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Get pairing code" }));
    expect(await screen.findByText("123456")).toBeInTheDocument();
    expect(screen.getByText("Waiting for the watch…")).toBeInTheDocument();
    expect(screen.getByText(/Valid for/)).toBeInTheDocument();

    r.push("paired");
    r.bpm(84);
    await tick(1000);
    expect(screen.getByText("Connected: Galaxy Watch")).toBeInTheDocument();
    expect(screen.getByText("84")).toBeInTheDocument();
    expect(screen.getByText("Galaxy Watch", { selector: ".badge" })).toBeInTheDocument();
    expect(screen.queryByText("Simulated")).not.toBeInTheDocument();
    expect(screen.queryByText("123456")).not.toBeInTheDocument();
  });

  it("shows the prompt, the demo alert note, and the OK answer", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { r, ui } = setup();
    render(ui);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Get pairing code" }));
    await screen.findByText("123456");
    r.push("paired");
    r.push("prompt");
    await tick(1000);
    expect(screen.getByText(/are you OK\?/i)).toBeInTheDocument();
    r.push("alert_sent", { status: "contact_not_opted_in" });
    await tick(1000);
    expect(screen.getByText(/demo, not sent/)).toBeInTheDocument();
    r.push("ack", { ok: true });
    await tick(1000);
    expect(screen.getByText("You said you are OK")).toBeInTheDocument();
    expect(screen.queryByText(/demo, not sent/)).not.toBeInTheDocument();
  });

  it("says when no reading arrived for 15 seconds, and recovers", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { r, ui } = setup();
    render(ui);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Get pairing code" }));
    await screen.findByText("123456");
    r.push("paired");
    r.bpm(80);
    await tick(1000);
    await tick(16_000);
    expect(screen.getByText(/No reading for 15 seconds/)).toBeInTheDocument();
    r.bpm(82);
    await tick(2000);
    expect(screen.getByText("Connected: Galaxy Watch")).toBeInTheDocument();
  });

  it("ends the trip on Stop and when the screen closes, and writes nothing to storage", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { r, ui } = setup();
    const { unmount } = render(ui);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Get pairing code" }));
    await screen.findByText("123456");
    await user.click(screen.getByRole("button", { name: "Stop and delete readings" }));
    expect(r.state.ended).toBe(true);

    r.state.ended = false;
    await user.click(screen.getByRole("button", { name: "Get pairing code" }));
    await screen.findByText("123456");
    unmount();
    expect(r.state.ended).toBe(true);
    expect(window.sessionStorage.length).toBe(0);
    expect(window.localStorage.length).toBe(0);
  });

  it("explains a failed pairing request in plain words", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { r, ui } = setup();
    r.state.fail = true;
    render(ui);
    await user.click(screen.getByRole("button", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Get pairing code" }));
    expect(await screen.findByText(/could not get a pairing code/i)).toBeInTheDocument();
  });

  it("uses careful wording and points to 911", () => {
    render(setup().ui);
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
