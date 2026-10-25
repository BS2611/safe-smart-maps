import { findBannedWording } from "./wording";

describe("findBannedWording", () => {
  it("allows the product name", () => {
    expect(findBannedWording("Welcome to Safe Smart Maps")).toEqual([]);
  });

  it("allows the CSS safe-area inset used for layout", () => {
    expect(findBannedWording("padding: env(safe-area-inset-top); safe-area insets")).toEqual([]);
  });

  it("allows the required disclaimer", () => {
    expect(
      findBannedWording("We describe conditions. We do not guarantee safety. In an emergency, call 911."),
    ).toEqual([]);
  });

  it("allows the approved wording", () => {
    expect(findBannedWording("Better lit and more active. Not sure.")).toEqual([]);
  });

  it.each([
    ["This route is safe", "safe"],
    ["Safest route", "Safest"],
    ["Safe Prioritized", "Safe"],
    ["Hazard Report", "Hazard"],
    ["a dangerous street", "dangerous"],
    ["crime-free area", "crime-free"],
  ])("flags %s", (text, match) => {
    const problems = findBannedWording(text);
    expect(problems.map((p) => p.match)).toContain(match);
  });

  it("still flags banned words next to the product name", () => {
    expect(findBannedWording("Safe Smart Maps says this is safe").map((p) => p.match)).toEqual(["safe"]);
  });

  it("returns a hint for each problem", () => {
    expect(findBannedWording("safest")[0].hint).toContain("Most lit");
  });
});
