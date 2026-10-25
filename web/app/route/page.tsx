import { RouteDetailGate } from "@/components/RouteDetailGate";

// One route's details. The route is chosen with ?id=... so the app can also be exported as static
// files for the Android app (a dynamic /routes/[id] path cannot be exported without knowing every id).
export default function RouteDetailPage() {
  return <RouteDetailGate />;
}
