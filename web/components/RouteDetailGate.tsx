"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { RouteDetailScreen } from "./RouteDetailScreen";

function Inner() {
  const id = useSearchParams().get("id") ?? "";
  return <RouteDetailScreen routeId={id} />;
}

export function RouteDetailGate() {
  return <Suspense fallback={<div className="screen" aria-busy="true" />}><Inner /></Suspense>;
}
