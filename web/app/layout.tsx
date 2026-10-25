import type { Metadata, Viewport } from "next";
import { Fraunces, Outfit } from "next/font/google";

import { TripProvider } from "@/components/TripProvider";

import "./globals.css";
import "./polish.css";

const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit", display: "swap" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });

export const metadata: Metadata = {
  title: "Safe Smart Maps",
  description: "Compare walking routes for the time you will be on the street.",
  icons: {
    icon: [
      { url: "/icons/logo.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "48x48" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  appleWebApp: { capable: true, title: "Smart Maps", statusBarStyle: "black-translucent" },
};

// viewport-fit=cover lets us use safe-area insets on iPhone.
export const viewport: Viewport = {
  width: "device-width", initialScale: 1, viewportFit: "cover", themeColor: "#07110e",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${outfit.variable} ${fraunces.variable}`}>
      <body>
        <TripProvider>{children}</TripProvider>
      </body>
    </html>
  );
}
