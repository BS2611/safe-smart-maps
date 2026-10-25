import { render, screen } from "@testing-library/react";

import { DISCLAIMER_TEXT, DisclaimerBanner, EMERGENCY_TEXT } from "./DisclaimerBanner";

describe("DisclaimerBanner", () => {
  it("shows the honesty notice and the emergency line", () => {
    render(<DisclaimerBanner />);
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeInTheDocument();
    expect(screen.getByText(EMERGENCY_TEXT)).toBeInTheDocument();
  });

  it("is exposed as a labelled region for screen readers", () => {
    render(<DisclaimerBanner />);
    expect(screen.getByRole("complementary", { name: "Important notice" })).toBeInTheDocument();
  });
});
