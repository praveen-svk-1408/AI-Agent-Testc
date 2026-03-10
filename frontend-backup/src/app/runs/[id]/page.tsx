"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTestRun } from "@/hooks/useTestRun";
import { useWebSocket } from "@/hooks/useWebSocket";
import RunResults from "@/components/RunResults";
import LoadingSpinner from "@/components/LoadingSpinner";
import type { WSEvent } from "@/types";

interface StepProgress {
  order: number;
  action: string;
  step: string;
  status: string;
  duration_ms: number;
  screenshot?: string;
  timestamp: string;
}

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const { run, loading, error, refetch } = useTestRun(runId);
  const { events, connected } = useWebSocket(
    run && (run.status === "pending" || run.status === "running") ? runId : null
  );
  const [liveScreenshot, setLiveScreenshot] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<StepProgress[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Process step events for live view
  useEffect(() => {
    const stepEvents = events.filter(
      (e): e is Extract<WSEvent, { event: "test_step" }> => e.event === "test_step"
    );
    const newSteps: StepProgress[] = [];
    for (const e of stepEvents) {
      if (e.order !== undefined) {
        newSteps.push({
          order: e.order,
          action: e.action || "",
          step: e.step,
          status: e.status || "passed",
          duration_ms: e.duration_ms || 0,
          screenshot: e.screenshot_base64,
          timestamp: e.timestamp,
        });
        if (e.screenshot_base64) {
          setLiveScreenshot(e.screenshot_base64);
        }
      }
    }
    if (newSteps.length > 0) {
      setCompletedSteps(newSteps);
    }
  }, [events]);

  // Auto-scroll the step log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [completedSteps]);

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
  const hasRefetched = useRef(false);
  useEffect(() => {
    if (isFinished && run && (run.status === "pending" || run.status === "running") && !hasRefetched.current) {
      hasRefetched.current = true;
      refetch();
    }
    if (!isFinished) {
      hasRefetched.current = false;
    }
  }, [isFinished, run?.status, refetch]);

  if (loading) return <LoadingSpinner className="py-12" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  if (!run) return <div className="text-gray-500">Run not found</div>;

  const isActive = run.status === "pending" || run.status === "running";
  const totalSteps = completedSteps.length;
  const passedSteps = completedSteps.filter((s) => s.status === "passed").length;
  const failedSteps = completedSteps.filter((s) => s.status === "failed").length;

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

      {/* Live Execution View */}
      {isActive && (
        <div className="mb-6">
          <div className="mb-3 flex items-center gap-2">
            <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-500" />
            <span className="text-sm font-semibold text-blue-800">
              {connected ? "Live Execution" : "Connecting..."}
            </span>
            {totalSteps > 0 && (
              <span className="ml-auto text-xs text-gray-500">
                {totalSteps} step{totalSteps !== 1 ? "s" : ""} completed
                {failedSteps > 0 && (
                  <span className="ml-1 text-red-500">({failedSteps} failed)</span>
                )}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
            {/* Browser View — live screenshot */}
            <div className="lg:col-span-3">
              <div className="overflow-hidden rounded-lg border-2 border-blue-200 bg-gray-900">
                {/* Browser chrome bar */}
                <div className="flex items-center gap-2 border-b border-gray-700 bg-gray-800 px-3 py-2">
                  <div className="flex gap-1.5">
                    <div className="h-3 w-3 rounded-full bg-red-500" />
                    <div className="h-3 w-3 rounded-full bg-yellow-500" />
                    <div className="h-3 w-3 rounded-full bg-green-500" />
                  </div>
                  <div className="ml-2 flex-1 rounded bg-gray-700 px-3 py-1 text-xs text-gray-300">
                    {run.browser} — {run.headed ? "headed" : "headless"}
                  </div>
                </div>
                {/* Screenshot area */}
                <div className="relative aspect-video bg-gray-950">
                  {liveScreenshot ? (
                    <img
                      src={liveScreenshot}
                      alt="Live browser view"
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <div className="text-center">
                        <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                        <p className="text-sm text-gray-400">
                          Waiting for browser to start...
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Step Log — live progress */}
            <div className="lg:col-span-2">
              <div className="flex h-full flex-col overflow-hidden rounded-lg border border-gray-200 bg-white">
                <div className="border-b border-gray-200 bg-gray-50 px-4 py-2.5">
                  <h3 className="text-sm font-semibold text-gray-700">Step Progress</h3>
                </div>
                <div className="flex-1 overflow-y-auto p-3" style={{ maxHeight: "400px" }}>
                  {completedSteps.length === 0 ? (
                    <p className="py-4 text-center text-xs text-gray-400">
                      Steps will appear here as they execute...
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {completedSteps.map((s, i) => (
                        <div
                          key={i}
                          className={`rounded-md border px-3 py-2 text-xs ${
                            s.status === "passed"
                              ? "border-green-200 bg-green-50"
                              : s.status === "failed"
                                ? "border-red-200 bg-red-50"
                                : "border-gray-200 bg-gray-50"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium">
                              {s.status === "passed" ? "✓" : s.status === "failed" ? "✗" : "○"}{" "}
                              Step {s.order}
                            </span>
                            <span className="text-gray-400">{s.duration_ms}ms</span>
                          </div>
                          <p className="mt-0.5 text-gray-600">{s.step}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  <div ref={logEndRef} />
                </div>
                {/* Progress bar */}
                {totalSteps > 0 && (
                  <div className="border-t border-gray-200 bg-gray-50 px-4 py-2">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-200">
                        <div
                          className="h-full rounded-full bg-green-500 transition-all"
                          style={{ width: `${(passedSteps / Math.max(totalSteps, 1)) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-500">
                        {passedSteps}/{totalSteps}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <RunResults run={run} />
    </div>
  );
}
