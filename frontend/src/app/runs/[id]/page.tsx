"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useTestRun } from "@/hooks/useTestRun";
import { useWebSocket } from "@/hooks/useWebSocket";
import RunResults from "@/components/RunResults";
import LoadingSpinner from "@/components/LoadingSpinner";
import type { WSEvent } from "@/types";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const { run, loading, error, refetch } = useTestRun(runId);
  const { events, connected } = useWebSocket(
    run && (run.status === "pending" || run.status === "running") ? runId : null
  );

  // Re-fetch when status changes via WebSocket
  const lastStatusEvent = [...events]
    .reverse()
    .find((e): e is Extract<WSEvent, { event: "status_change" }> => e.event === "status_change");
  const isFinished =
    lastStatusEvent &&
    (lastStatusEvent.status === "passed" ||
      lastStatusEvent.status === "failed" ||
      lastStatusEvent.status === "error");

  // Auto-refetch when run finishes
  if (isFinished && run && (run.status === "pending" || run.status === "running")) {
    refetch();
  }

  // Extract step events for progress display
  const stepEvents = events.filter(
    (e): e is Extract<WSEvent, { event: "test_step" }> => e.event === "test_step"
  );

  if (loading) return <LoadingSpinner className="py-12" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  if (!run) return <div className="text-gray-500">Run not found</div>;

  const isActive = run.status === "pending" || run.status === "running";

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="mb-6 text-sm text-gray-500">
        <Link href="/runs" className="hover:text-blue-600">Runs</Link>
        <span className="mx-2">/</span>
        <span className="font-mono text-gray-900">{run.id.slice(0, 8)}...</span>
      </nav>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Test Run Detail</h1>
        <p className="mt-1 font-mono text-xs text-gray-400">{run.id}</p>
      </div>

      {/* Live Progress */}
      {isActive && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
            <span className="text-sm font-medium text-blue-800">
              {connected ? "Connected — Live Updates" : "Connecting..."}
            </span>
          </div>
          {stepEvents.length > 0 && (
            <div className="max-h-48 overflow-y-auto rounded bg-gray-900 p-3 font-mono text-xs text-green-400">
              {stepEvents.map((e, i) => (
                <div key={i}>{e.step}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <RunResults run={run} />
    </div>
  );
}
