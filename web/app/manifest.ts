import type { MetadataRoute } from "next";

export const dynamic = "force-static"; // needed for the static Android export

// Lets people add the app to the home screen on Android and iPhone (docs/specs/TECHNICAL_SPEC.md 8.1).
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Safe Smart Maps",
    short_name: "Smart Maps",
    description: "Compare walking routes for the time you will be on the street.",
    start_url: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#101413",
    theme_color: "#101413",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
