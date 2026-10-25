import { RouteDetailScreen } from "@/components/RouteDetailScreen";

export default async function RouteDetailPage({ params }: { params: Promise<{ routeId: string }> }) {
  const { routeId } = await params;
  return <RouteDetailScreen routeId={routeId} />;
}
