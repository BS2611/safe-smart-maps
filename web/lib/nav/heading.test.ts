import { arrowRotation, chooseHeading, headingFromOrientation, mapBearing } from "./heading";

describe("heading math", () => {
  it("normalizes orientation into a clockwise compass heading", () => {
    expect(headingFromOrientation({ alpha: null, webkitCompassHeading: -90 })).toBe(270);
    expect(headingFromOrientation({ alpha: 90, absolute: true, webkitCompassHeading: 15 })).toBe(15);
    expect(headingFromOrientation({ alpha: 90, absolute: true })).toBe(270);
    expect(headingFromOrientation({ alpha: 20, absolute: false })).toBeNull();
    expect(headingFromOrientation({ alpha: null })).toBeNull();
  });

  it("prefers the compass and otherwise uses a usable GPS course", () => {
    expect(chooseHeading(10, 200)).toEqual({ degrees: 10, source: "compass" });
    expect(chooseHeading(null, 200)).toEqual({ degrees: 200, source: "course" });
    expect(chooseHeading(null, -1)).toEqual({ degrees: null, source: "none" });
    expect(chooseHeading(Number.NaN, null)).toEqual({ degrees: null, source: "none" });
  });

  it("turns the map in heading-up mode and turns the arrow in north-up mode", () => {
    expect(mapBearing(84, "heading-up")).toBe(84);
    expect(mapBearing(84, "north-up")).toBe(0);
    expect(mapBearing(null, "heading-up")).toBe(0);
    expect(arrowRotation(84, "heading-up")).toBe(0);
    expect(arrowRotation(84, "north-up")).toBe(84);
    expect(arrowRotation(null, "north-up")).toBe(0);
  });
});
