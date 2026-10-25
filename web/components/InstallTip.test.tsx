import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { detectPlatform, InstallTip } from "./InstallTip";

const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1";
const ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36";
const DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36";

function setup(userAgent: string, standalone = false) {
  Object.defineProperty(navigator, "userAgent", { configurable: true, value: userAgent });
  window.matchMedia = ((q: string) => ({ matches: standalone && q.includes("standalone"), addEventListener() {}, removeEventListener() {} })) as never;
}

describe("detectPlatform", () => {
  it("tells iPhone, iPad, Android and desktop apart", () => {
    expect(detectPlatform(IPHONE)).toBe("ios");
    expect(detectPlatform("Mozilla/5.0 (iPad; CPU OS 17_0)")).toBe("ios");
    expect(detectPlatform("Mozilla/5.0 (Macintosh; Intel Mac OS X)", 5)).toBe("ios"); // iPad in desktop mode
    expect(detectPlatform("Mozilla/5.0 (Macintosh; Intel Mac OS X)", 0)).toBe("other");
    expect(detectPlatform(ANDROID)).toBe("android");
    expect(detectPlatform(DESKTOP)).toBe("other");
  });
});

describe("InstallTip", () => {
  it("shows the iPhone steps", () => {
    setup(IPHONE);
    render(<InstallTip />);
    expect(screen.getByRole("complementary", { name: "Install for best results" })).toBeInTheDocument();
    expect(screen.getByText(/Add to Home Screen/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add to home screen" })).not.toBeInTheDocument();
  });

  it("offers the install button on Android once the browser allows it", async () => {
    setup(ANDROID);
    render(<InstallTip />);
    expect(screen.queryByRole("button", { name: "Add to home screen" })).not.toBeInTheDocument();
    const prompt = vi.fn().mockResolvedValue(undefined);
    await act(async () => {
      const event = Object.assign(new Event("beforeinstallprompt", { cancelable: true }), { prompt });
      window.dispatchEvent(event);
    });
    await userEvent.setup().click(screen.getByRole("button", { name: "Add to home screen" }));
    expect(prompt).toHaveBeenCalled();
  });

  it("is hidden on desktop and when already installed", () => {
    setup(DESKTOP);
    const { container, unmount } = render(<InstallTip />);
    expect(container).toBeEmptyDOMElement();
    unmount();
    setup(IPHONE, true);
    const second = render(<InstallTip />);
    expect(second.container).toBeEmptyDOMElement();
  });

  it("is hidden inside the Android app, where there is nothing to install", () => {
    setup(ANDROID);
    (window as unknown as { Capacitor: unknown }).Capacitor = { isNativePlatform: () => true };
    const { container } = render(<InstallTip />);
    expect(container).toBeEmptyDOMElement();
    delete (window as unknown as { Capacitor?: unknown }).Capacitor;
  });

  it("remembers 'Not now'", async () => {
    setup(IPHONE);
    const { unmount } = render(<InstallTip />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    unmount();
    render(<InstallTip />);
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    window.localStorage.clear();
  });
});
