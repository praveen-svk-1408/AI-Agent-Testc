"use client";

import Link from "next/link";
import { useTestRuns } from "@/hooks/useTestRun";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";
import { formatDate, formatDuration } from "@/lib/utils";

export default function RunsListPage() {
  const { runs, loading, error } = useTestRuns();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Test Runs</h1>
        <p className="mt-1 text-sm text-gray-500">View all test execution runs and results</p>
      </div>

      {loading && <LoadingSpinner className="py-12" />}

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {!loading && !error && runs.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 py-12 text-center">
          <h3 className="text-sm font-medium text-gray-900">No test runs</h3>
          <p className="mt-1 text-sm text-gray-500">
            Runs will appear here after you execute a test case.
          </p>
        </div>
      )}

      {!loading && runs.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Browser</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Created</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Run ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <StatusBadge status={run.status} type="run" />
                  </td>
                  <td className="px-4 py-3 text-sm capitalize text-gray-600">{run.browser}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatDuration(run.duration_ms)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{formatDate(run.created_at)}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/runs/${run.id}`}
                      className="font-mono text-xs text-blue-600 hover:underline"
                    >
                      {run.id.slice(0, 8)}...
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
