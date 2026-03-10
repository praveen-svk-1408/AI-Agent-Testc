"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import * as api from "@/services/api";
import TestStepTable from "@/components/TestStepTable";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";
import GenerationProgress from "@/components/GenerationProgress";
import { useWebSocket } from "@/hooks/useWebSocket";
import { formatDate } from "@/lib/utils";
import type { TestCaseDetail, TestRun, WSEvent, UpdateTestStepData } from "@/types";

interface LiveStep {
  order: number;
  action: string;
  step: string;
  status: string;
  duration_ms: number;
  screenshot?: string;
}

export default function CaseDetailPage() {
  const params = useParams();
  const suiteId = params.id as string;
  const caseId = params.caseId as string;

  const [testCase, setTestCase] = useState<TestCaseDetail | null>(null);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [savingSteps, setSavingSteps] = useState(false);

  // Live runner state
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [liveScreenshot, setLiveScreenshot] = useState<string | null>(null);
  const [liveSteps, setLiveSteps] = useState<LiveStep[]>([]);
  const [runningBrowser, setRunningBrowser] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // WebSocket for live updates
  const { events, connected } = useWebSocket(
    activeRunId && (runStatus === "pending" || runStatus === "running") ? activeRunId : null
  );

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [caseData, runsData] = await Promise.all([
        api.getTestCase(caseId),
        api.getTestRuns(caseId),
      ]);
      setTestCase(caseData);
      setRuns(runsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Process WebSocket events for live view
  useEffect(() => {
    const newSteps: LiveStep[] = [];
    let finalStatus: string | null = null;

    for (const e of events) {
      if (e.event === "test_step" && e.order !== undefined) {
        const stepEvent = e as Extract<WSEvent, { event: "test_step" }>;
        newSteps.push({
          order: stepEvent.order!,
          action: stepEvent.action || "",
          step: stepEvent.step,
          status: stepEvent.status || "passed",
          duration_ms: stepEvent.duration_ms || 0,
          screenshot: stepEvent.screenshot_base64,
        });
        if (stepEvent.screenshot_base64) {
          setLiveScreenshot(stepEvent.screenshot_base64);
        }
      }
      if (e.event === "status_change") {
        finalStatus = (e as Extract<WSEvent, { event: "status_change" }>).status;
      }
    }
    if (newSteps.length > 0) {
      setLiveSteps(newSteps);
    }
    if (finalStatus && finalStatus !== "running" && finalStatus !== "pending") {
      setRunStatus(finalStatus);
      // Refresh runs list after completion
      fetchData();
    }
  }, [events, fetchData]);

  // Auto-scroll step log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveSteps]);

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      await api.triggerGeneration(caseId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Generation failed");
      setGenerating(false);
    }
  };

  const handleGenerationComplete = useCallback(() => {
    setGenerating(false);
    fetchData();
  }, [fetchData]);

  const handleSaveSteps = useCallback(async (steps: UpdateTestStepData[]) => {
    try {
      setSavingSteps(true);
      const updated = await api.updateTestSteps(caseId, steps);
      setTestCase(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to save steps");
    } finally {
      setSavingSteps(false);
    }
  }, [caseId]);

  const handleRunTest = async (browser: "chromium" | "firefox" | "webkit") => {
    try {
      // Reset live runner state
      setLiveScreenshot(null);
      setLiveSteps([]);
      setRunStatus("pending");
      setRunningBrowser(browser);

      const run = await api.createTestRun({ case_id: caseId, browser, headed: false });
      setActiveRunId(run.id);
      setRunStatus("running");
    } catch (err) {
      setRunStatus(null);
      setRunningBrowser(null);
      alert(err instanceof Error ? err.message : "Failed to create run");
    }
  };

  const isRunning = runStatus === "pending" || runStatus === "running";

  if (loading) return <LoadingSpinner className="py-12" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  if (!testCase) return <div className="text-gray-500">Test case not found</div>;

  const passedSteps = liveSteps.filter((s) => s.status === "passed").length;
  const failedSteps = liveSteps.filter((s) => s.status === "failed").length;

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="mb-4 text-sm text-gray-500">
        <Link href="/" className="hover:text-blue-600">Dashboard</Link>
        <span className="mx-2">/</span>
        <Link href={`/suites/${suiteId}`} className="hover:text-blue-600">Suite</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{testCase.title}</span>
      </nav>

      {/* Case Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{testCase.title}</h1>
            <StatusBadge status={testCase.status} type="case" />
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium capitalize text-gray-600">
              {testCase.test_type}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">{testCase.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleGenerate}
            disabled={generating || testCase.status === "generating"}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {generating ? "Generating..." : "Generate Steps"}
          </button>
        </div>
      </div>

      {/* Generation Progress */}
      <GenerationProgress
        caseId={caseId}
        isGenerating={generating}
        onComplete={handleGenerationComplete}
      />

      {/* Run buttons */}
      <div className="mb-4 flex items-center gap-3">
        <span className="text-sm font-medium text-gray-700">Run on:</span>
        {(["chromium", "firefox", "webkit"] as const).map((browser) => (
          <button
            key={browser}
            onClick={() => handleRunTest(browser)}
            disabled={isRunning}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium capitalize text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {isRunning && runningBrowser === browser ? (
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
                Running...
              </span>
            ) : (
              browser
            )}
          </button>
        ))}
      </div>

      {/* Split Layout: Steps (left) | Live Runner (right) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* LEFT: Test Steps */}
        <div className="flex flex-col">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              Test Steps ({testCase.test_steps.length})
            </h2>
          </div>
          <div className="flex-1 overflow-hidden rounded-lg border border-gray-200 bg-white">
            <TestStepTable
              steps={testCase.test_steps}
              onSave={handleSaveSteps}
              saving={savingSteps}
            />
          </div>

          {/* Recent Runs (compact) */}
          {runs.length > 0 && (
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-700">
                Recent Runs ({runs.length})
              </h3>
              <div className="space-y-1.5">
                {runs.slice(0, 5).map((run) => (
                  <Link
                    key={run.id}
                    href={`/runs/${run.id}`}
                    className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-xs hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-2">
                      <StatusBadge status={run.status} type="run" />
                      <span className="capitalize text-gray-600">{run.browser}</span>
                    </div>
                    <span className="text-gray-400">{formatDate(run.created_at)}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Live Runner */}
        <div className="flex flex-col">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Live Runner</h2>
            {runStatus && !isRunning && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  runStatus === "passed"
                    ? "bg-green-100 text-green-700"
                    : runStatus === "failed"
                      ? "bg-red-100 text-red-700"
                      : "bg-yellow-100 text-yellow-700"
                }`}
              >
                {runStatus}
              </span>
            )}
          </div>

          {/* Browser viewport */}
          <div className="overflow-hidden rounded-lg border-2 border-gray-200 bg-gray-900">
            {/* Browser chrome */}
            <div className="flex items-center gap-2 border-b border-gray-700 bg-gray-800 px-3 py-1.5">
              <div className="flex gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-red-500" />
                <div className="h-2.5 w-2.5 rounded-full bg-yellow-500" />
                <div className="h-2.5 w-2.5 rounded-full bg-green-500" />
              </div>
              <div className="ml-2 flex-1 rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
                {runningBrowser || "chromium"} — headless
                {isRunning && (
                  <span className="ml-2 text-blue-400">● recording</span>
                )}
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
                    {isRunning ? (
                      <>
                        <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                        <p className="text-sm text-gray-400">
                          Starting browser...
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-gray-500">
                        Click a browser button above to start a test run
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Step progress log */}
          <div className="mt-3 flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div className="border-b border-gray-200 bg-gray-50 px-3 py-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-gray-700">Step Progress</h3>
                {liveSteps.length > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`h-full rounded-full transition-all ${failedSteps > 0 ? "bg-red-500" : "bg-green-500"}`}
                        style={{
                          width: `${(liveSteps.length / Math.max(testCase.test_steps.length, 1)) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">
                      {passedSteps}/{testCase.test_steps.length}
                    </span>
                  </div>
                )}
              </div>
            </div>
            <div className="max-h-52 overflow-y-auto p-2">
              {liveSteps.length === 0 ? (
                <p className="py-4 text-center text-xs text-gray-400">
                  {isRunning ? "Waiting for steps..." : "Run a test to see step-by-step progress"}
                </p>
              ) : (
                <div className="space-y-1.5">
                  {liveSteps.map((s, i) => (
                    <div
                      key={i}
                      className={`rounded border px-2.5 py-1.5 text-xs ${
                        s.status === "passed"
                          ? "border-green-200 bg-green-50 text-green-800"
                          : s.status === "failed"
                            ? "border-red-200 bg-red-50 text-red-800"
                            : "border-gray-200 bg-gray-50 text-gray-600"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          {s.status === "passed" ? "✓" : s.status === "failed" ? "✗" : "○"}{" "}
                          Step {s.order}: <span className="font-normal">{s.action}</span>
                        </span>
                        <span className="text-gray-400">{s.duration_ms}ms</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
