import {
  basicCenterForHeading, bearingDeg, darkestSegmentIndex, forwardBearing, haversineM,
  nearestIndex, nearestSegmentIndex, sampleRoute, segmentMidpoint,
} from "./geo";

describe("street view geometry", () => {
  it("measures distance and compass bearing", () => {
    expect(haversineM(-122.4, 37.8, -122.4, 37.8)).toBe(0);
    expect(haversineM(0, 0, 0, 0.01)).toBeGreaterThan(1000);
    expect(haversineM(0, 0, 0, 0.01)).toBeLessThan(1200);
    expect(bearingDeg(0, 0, 0, 1)).toBeCloseTo(0, 5);
    expect(bearingDeg(0, 0, 1, 0)).toBeCloseTo(90, 5);
  });

  it("samples a line about every step, including both ends", () => {
    const north = 100 / 111_320;
    const samples = sampleRoute([[-122.4, 37.8], [-122.4, 37.8 + north]], 25);
    expect(samples[0]).toEqual([-122.4, 37.8]);
    expect(samples[samples.length - 1][1]).toBeCloseTo(37.8 + north, 5);
    expect(samples.length).toBeGreaterThanOrEqual(4);
    expect(samples.length).toBeLessThanOrEqual(6);
    expect(sampleRoute([], 25)).toEqual([]);
    expect(sampleRoute([[1, 2]], 25)).toEqual([[1, 2]]);
  });

  it("skips a repeated point and still keeps the end", () => {
    const samples = sampleRoute([[0, 0], [0, 0], [0, 0.002]], 50);
    expect(samples[0]).toEqual([0, 0]);
    expect(samples[samples.length - 1][1]).toBeCloseTo(0.002, 6);
  });

  it("picks the nearest sample and the forward heading", () => {
    const samples: [number, number][] = [[0, 0], [0, 0.001], [0.001, 0.001]];
    expect(nearestIndex(samples, 0.0009, 0.001)).toBe(2);
    expect(nearestIndex([], 0, 0)).toBe(0);
    expect(forwardBearing(samples, 0)).toBeCloseTo(0, 4);
    expect(forwardBearing(samples, 2)).toBeCloseTo(bearingDeg(0, 0.001, 0.001, 0.001), 5);
    expect(forwardBearing([[0, 0]], 0)).toBe(0);
  });

  it("finds the nearest stretch and its midpoint", () => {
    const segments = [
      { start: [0, 0] as [number, number], end: [0, 0.01] as [number, number] },
      { start: [0.01, 0] as [number, number], end: [0.02, 0] as [number, number] },
    ];
    expect(nearestSegmentIndex(segments, 0.015, 0)).toBe(1);
    expect(nearestSegmentIndex([], 1, 1)).toBe(0);
    expect(segmentMidpoint(segments[1])).toEqual([0.015, 0]);
  });

  it("treats an unknown score as not sure, not as the darkest", () => {
    expect(darkestSegmentIndex([{ score: null }, { score: 40 }, { score: 12 }, { score: 12 }])).toBe(2);
    expect(darkestSegmentIndex([{ score: null }, { score: Number.NaN }])).toBeNull();
    expect(darkestSegmentIndex([])).toBeNull();
  });

  it("turns a 360 photo toward the walk", () => {
    expect(basicCenterForHeading(10, 10)).toEqual([0.5, 0.5]);
    expect(basicCenterForHeading(0, 90)[0]).toBeCloseTo(0.75, 5);
    expect(basicCenterForHeading(10, 350)[0]).toBeCloseTo(0.5 - 20 / 360, 5);
  });
});
