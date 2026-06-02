import RunDetailDashboard from "@/components/RunDetailDashboard";

type Props = {
  params: Promise<{ runId: string }>;
};

export default async function RunPage({ params }: Props) {
  const { runId } = await params;
  return <RunDetailDashboard runId={runId} />;
}
