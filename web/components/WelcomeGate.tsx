"use client";

import { useEffect, useState } from "react";

import { WelcomeScreen } from "./WelcomeScreen";

/** Shows the "location is off" welcome when the browser already says location is blocked.
 *  It only reads the permission state; it never asks for location. */
export function WelcomeGate() {
  const [off, setOff] = useState(false);
  useEffect(() => {
    let cancelled = false;
    try {
      navigator.permissions?.query({ name: "geolocation" }).then((status) => {
        if (!cancelled) setOff(status.state === "denied");
      }, () => undefined);
    } catch {
      // Permissions API missing (older Safari): show the normal welcome
    }
    return () => { cancelled = true; };
  }, []);
  return <WelcomeScreen locationOff={off} />;
}
