import { vi } from "vitest";

import { selectStreetViewProvider, streetViewSourceName } from "./provider";

describe("street view provider choice", () => {
  it("uses Mapillary unless a Google browser key is set", () => {
    vi.stubEnv("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", "");
    vi.stubEnv("NEXT_PUBLIC_MAPILLARY_TOKEN", "from-env");
    const fromEnv = selectStreetViewProvider();
    expect(fromEnv.id).toBe("mapillary");
    expect(fromEnv.configured).toBe(true);

    const mapillary = selectStreetViewProvider({ googleKey: "  ", mapillaryToken: "abc" });
    expect(mapillary.id).toBe("mapillary");
    expect(mapillary.configured).toBe(true);

    const google = selectStreetViewProvider({ googleKey: "g-key", mapillaryToken: "abc" });
    expect(google.id).toBe("google");
    expect(google.configured).toBe(true);

    const missing = selectStreetViewProvider({ googleKey: "", mapillaryToken: "" });
    expect(missing.id).toBe("mapillary");
    expect(missing.configured).toBe(false);
  });

  it("names the photo source", () => {
    expect(streetViewSourceName("mapillary")).toBe("Mapillary");
    expect(streetViewSourceName("google")).toBe("Google Street View");
  });
});
