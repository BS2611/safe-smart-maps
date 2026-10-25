import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { TripProvider } from "@/components/TripProvider";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "Safe Smart Maps",
  description: "Compare walking routes for the time you will be on the street.",
};

// viewport-fit=cover lets us use safe-area insets on iPhone.
export const viewport: Viewport = {
  width: "device-width", initialScale: 1, viewportFit: "cover", themeColor: "#101413",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <TripProvider>{children}</TripProvider>
      </body>
    </html>
  );
}
