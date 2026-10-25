import { loadFixture } from "@/test-utils/fixtures";

import { alertAhead } from "./alerts";

describe("stretch heads-up", () => {
  const route = loadFixture().routes[0];

  it("warns when the next stretch is low-scoring or has no open places", () => {
    const alert = alertAhead(route, 0, 20);
    expect(alert).not.toBeNull();
    expect(alert?.title).toMatch(/Next stretch|Open places thin out/);
    expect(alert?.detail).toMatch(/Score/);
  });
});
