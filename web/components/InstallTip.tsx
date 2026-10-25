"use client";

import { useEffect, useState } from "react";

type Platform = "ios" | "android" | "other";

export function detectPlatform(userAgent: string, maxTouchPoints = 0): Platform {
  if (/iphone|ipad|ipod/i.test(userAgent) || (/macintosh/i.test(userAgent) && maxTouchPoints > 1)) return "ios";
  if (/android/i.test(userAgent)) return "android";
  return "other";
}

type InstallEvent = Event & { prompt: () => Promise<void> };

/** Short "add to home screen" tip. Hidden once the app is installed, or on desktop. */
export function InstallTip() {
  const [platform, setPlatform] = useState<Platform>("other");
  const [installed, setInstalled] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [prompt, setPrompt] = useState<InstallEvent | null>(null);

  useEffect(() => {
    setPlatform(detectPlatform(navigator.userAgent, navigator.maxTouchPoints));
    const standalone = window.matchMedia?.("(display-mode: standalone)").matches
      || (navigator as unknown as { standalone?: boolean }).standalone === true;
    setInstalled(Boolean(standalone));
    try { setDismissed(window.localStorage.getItem("ssm.install.dismissed") === "1"); } catch { /* blocked */ }
    const onPrompt = (e: Event) => { e.preventDefault(); setPrompt(e as InstallEvent); };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  if (installed || dismissed || platform === "other") return null;

  function dismiss() {
    setDismissed(true);
    try { window.localStorage.setItem("ssm.install.dismissed", "1"); } catch { /* blocked */ }
  }

  return (
    <aside className="banner info" aria-label="Install for best results">
      <h3>Install for best results</h3>
      {platform === "ios" ? (
        <p className="small muted">
          In Safari, tap the Share button, then <strong>Add to Home Screen</strong>. The app opens full screen and
          keeps the screen on while you walk.
        </p>
      ) : (
        <p className="small muted">
          Add Safe Smart Maps to your home screen so it opens full screen like an app.
        </p>
      )}
      <div className="row" style={{ marginTop: 8 }}>
        {platform === "android" && prompt ? (
          <button type="button" className="btn small primary"
            onClick={async () => { await prompt.prompt(); setPrompt(null); }}>Add to home screen</button>
        ) : null}
        <button type="button" className="btn small secondary" onClick={dismiss}>Not now</button>
      </div>
    </aside>
  );
}
