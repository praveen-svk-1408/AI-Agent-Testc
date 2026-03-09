"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import * as api from "@/services/api";
import TestStepTable from "@/components/TestStepTable";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";
import GenerationProgress from "@/components/GenerationProgress";
import { formatDate } from "@/lib/utils";
import type { TestCaseDetail, TestRun } from "@/types";

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const suiteId = params.id as string;
  const caseId = params.caseId as string;

  const [testCase, setTestCase] = useState<TestCaseDetail | null>(null);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

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

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      await api.triggerGeneration(caseId);
      // Don't refetch immediately - let the GenerationProgress component handle polling
    } catch (err) {
      alert(err instanceof Error ? err.message : "Generation failed");
      setGenerating(false);
    }
  };

  const handleGenerationComplete = useCallback(() => {
    setGenerating(false);
    fetchData();
  }, [fetchData]);

  const handleRunTest = async (browser: "chromium" | "firefox" | "webkit") => {
    try {
      const run = await api.createTestRun({ case_id: caseId, browser });
      // Navigate to the run detail page to see live progress
      router.push(`/runs/${run.id}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create run");
    }
  };

  if (loading) return <LoadingSpinner className="py-12" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  if (!testCase) return <div className="text-gray-500">Test case not found</div>;

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="mb-6 text-sm text-gray-500">
        <Link href="/" className="hover:text-blue-600">Dashboard</Link>
        <span className="mx-2">/</span>
        <Link href={`/suites/${suiteId}`} className="hover:text-blue-600">Suite</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{testCase.title}</span>
      </nav>

      {/* Case Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{testCase.title}</h1>
            <StatusBadge status={testCase.status} type="case" />
          </div>
          <p className="mt-2 text-gray-500">{testCase.description}</p>
          <p className="mt-1 text-xs text-gray-400">
            Created {formatDate(testCase.created_at)} · Attempts: {testCase.generation_attempts}
          </p>
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

      {/* Test Steps */}
      <div className="mb-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Generated Steps</h2>
        <div className="rounded-lg border border-gray-200 bg-white">
          <TestStepTable steps={testCase.test_steps} />
        </div>
      </div>

      {/* Run Test */}
      <div className="mb-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Run Test</h2>
        <div className="flex gap-2">
          {(["chromium", "firefox", "webkit"] as const).map((browser) => (
            <button
              key={browser}
              onClick={() => handleRunTest(browser)}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium capitalize text-gray-700 hover:bg-gray-50"
            >
              Run on {browser}
            </button>
          ))}
        </div>
      </div>

      {/* Recent Runs */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">
          Recent Runs ({runs.length})
        </h2>
        {runs.length === 0 ? (
          <p className="text-sm text-gray-400">No runs yet.</p>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <Link
                key={run.id}
                href={`/runs/${run.id}`}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3 hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge status={run.status} type="run" />
                  <span className="text-sm capitalize text-gray-600">{run.browser}</span>
                </div>
                <span className="text-xs text-gray-400">{formatDate(run.created_at)}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
