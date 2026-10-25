import { render, screen, waitFor } from "@testing-library/react";

import { findBannedWording } from "@/lib/wording";

import { WelcomeGate } from "./WelcomeGate";
import { WelcomeScreen } from "./WelcomeScreen";

describe("WelcomeScreen", () => {
  it("explains the idea, shows the honesty notice and the way forward", () => {
    render(<WelcomeScreen />);
    expect(screen.getByRole("heading", { level: 1, name: "See more of the walk ahead." })).toBeInTheDocument();
    for (const t of ["Three routes", "Reasons shown", "Time matters"]) {
      expect(screen.getByRole("heading", { name: t })).toBeInTheDocument();
    }
    expect(screen.getByText("We describe conditions. We do not guarantee safety.")).toBeInTheDocument();
    expect(screen.getByText("In an emergency, call 911.")).toBeInTheDocument();
    expect(screen.getByText("This trip stays in this tab. Sharing is optional.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get started" })).toHaveAttribute("href", "/plan");
    expect(screen.getByRole("link", { name: /How scores work/ })).toHaveAttribute("href", "/how-scores-work");
    expect(screen.getByText("You can type your start. GPS is optional.")).toBeInTheDocument();
    expect(screen.queryByText(/Location is off/)).not.toBeInTheDocument();
  });

  it("when location is off it asks for a starting point and does not need GPS", () => {
    render(<WelcomeScreen locationOff />);
    expect(screen.getByRole("status")).toHaveTextContent("Location is off. Enter a starting point to continue.");
    expect(screen.getByRole("status")).toHaveTextContent("without enabling GPS");
    expect(screen.getByRole("link", { name: "Enter starting point" })).toHaveAttribute("href", "/plan");
    expect(screen.queryByRole("link", { name: "Get started" })).not.toBeInTheDocument();
  });

  it("describes the picture for screen readers and never says safe", () => {
    const { container } = render(<WelcomeScreen />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/lit route curves around a weaker stretch/i);
    expect(findBannedWording(container.textContent ?? "")).toEqual([]);
  });
});

describe("WelcomeGate", () => {
  function stubPermission(state: string | "missing" | "throws") {
    const nav = navigator as unknown as { permissions?: unknown };
    Object.defineProperty(nav, "permissions", {
      configurable: true,
      value: state === "missing" ? undefined : {
        query: () => state === "throws" ? Promise.reject(new Error("no")) : Promise.resolve({ state }),
      },
    });
  }

  it("shows the location-off welcome when the browser says denied", async () => {
    stubPermission("denied");
    render(<WelcomeGate />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Location is off"));
  });

  it.each(["prompt", "granted", "missing", "throws"])("shows the normal welcome when permission is %s", async (state) => {
    stubPermission(state);
    render(<WelcomeGate />);
    await waitFor(() => expect(screen.getByRole("link", { name: "Get started" })).toBeInTheDocument());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
