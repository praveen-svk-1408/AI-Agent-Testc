"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTestSuite } from "@/hooks/useTestSuites";
import CreateCaseModal from "@/components/CreateCaseModal";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";
import { formatDate } from "@/lib/utils";
import * as api from "@/services/api";
import type { CreateTestCaseRequest } from "@/types";

export default function SuiteDetailPage() {
  const params = useParams();
  const suiteId = params.id as string;
  const { suite, loading, error, refetch } = useTestSuite(suiteId);
  const [modalOpen, setModalOpen] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  const handleCreateCase = async (data: CreateTestCaseRequest) => {
    await api.createTestCase(suiteId, data);
    refetch();
  };

  const handleGenerate = async (caseId: string) => {
    try {
      setGeneratingId(caseId);
      await api.triggerGeneration(caseId);
      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const status = await api.getGenerationStatus(caseId);
          if (
            status.case_status === "generated" ||
            status.case_status === "failed" ||
            status.case_status === "draft"
          ) {
            clearInterval(pollInterval);
            setGeneratingId(null);
            refetch();
          }
        } catch {
          clearInterval(pollInterval);
          setGeneratingId(null);
          refetch();
        }
      }, 3000);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Generation failed");
      setGeneratingId(null);
    }
  };

  const handleDeleteCase = async (caseId: string) => {
    if (confirm("Delete this test case?")) {
      await api.deleteTestCase(caseId);
      refetch();
    }
  };

  if (loading) return <LoadingSpinner className="py-12" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  if (!suite) return <div className="text-gray-500">Suite not found</div>;

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="mb-6 text-sm text-gray-500">
        <Link href="/" className="hover:text-blue-600">Dashboard</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{suite.name}</span>
      </nav>

      {/* Suite Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{suite.name}</h1>
        {suite.description && <p className="mt-1 text-gray-500">{suite.description}</p>}
        <div className="mt-2 flex items-center gap-4 text-sm text-gray-400">
          <span>{suite.base_url}</span>
          <span>Created {formatDate(suite.created_at)}</span>
        </div>
      </div>

      {/* Test Cases */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Test Cases ({suite.test_cases.length})
        </h2>
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New Test Case
        </button>
      </div>

      {suite.test_cases.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 py-12 text-center">
          <h3 className="text-sm font-medium text-gray-900">No test cases yet</h3>
          <p className="mt-1 text-sm text-gray-500">
            Create a test case by describing it in natural language.
          </p>
          <button
            onClick={() => setModalOpen(true)}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + New Test Case
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {suite.test_cases.map((tc) => (
            <div
              key={tc.id}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Link
                    href={`/suites/${suiteId}/cases/${tc.id}`}
                    className="font-medium text-gray-900 hover:text-blue-600"
                  >
                    {tc.title}
                  </Link>
                  <StatusBadge status={tc.status} type="case" />
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium capitalize text-gray-600">
                    {tc.test_type}
                  </span>
                </div>
                <p className="mt-1 truncate text-sm text-gray-500">{tc.description}</p>
              </div>
              <div className="ml-4 flex items-center gap-2">
                <button
                  onClick={() => handleGenerate(tc.id)}
                  disabled={tc.status === "generating" || generatingId === tc.id}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  {generatingId === tc.id || tc.status === "generating"
                    ? "Generating..."
                    : "Generate"}
                </button>
                <button
                  onClick={() => handleDeleteCase(tc.id)}
                  className="rounded p-1 text-gray-400 hover:text-red-500"
                  title="Delete"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateCaseModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreateCase}
      />
    </div>
  );
}
