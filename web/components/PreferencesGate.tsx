"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { PreferencesScreen } from "./PreferencesScreen";

const ALLOWED = new Set(["/plan", "/routes"]);

function Inner() {
  const params = useSearchParams();
  const next = params.get("next");
  // Only our own pages are allowed as the place to return to.
  return <PreferencesScreen next={next && ALLOWED.has(next) ? next : "/plan"} />;
}

export function PreferencesGate() {
  return <Suspense fallback={<div className="screen" aria-busy="true" />}><Inner /></Suspense>;
}
