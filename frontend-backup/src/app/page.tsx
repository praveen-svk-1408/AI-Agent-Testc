"use client";

import { useState } from "react";
import { useTestSuites } from "@/hooks/useTestSuites";
import SuiteCard from "@/components/SuiteCard";
import CreateSuiteModal from "@/components/CreateSuiteModal";
import LoadingSpinner from "@/components/LoadingSpinner";
import type { CreateTestSuiteRequest } from "@/types";

export default function DashboardPage() {
  const { suites, loading, error, create, remove } = useTestSuites();
  const [modalOpen, setModalOpen] = useState(false);

  const handleCreate = async (data: CreateTestSuiteRequest) => {
    await create(data);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this test suite?")) {
      await remove(id);
    }
  };

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Test Suites</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your test suites and generate Playwright tests
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New Suite
        </button>
      </div>

      {loading && <LoadingSpinner className="py-12" />}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && suites.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 py-12 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <h3 className="mt-4 text-sm font-medium text-gray-900">No test suites</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by creating a new test suite.</p>
          <button
            onClick={() => setModalOpen(true)}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + New Suite
          </button>
        </div>
      )}

      {!loading && suites.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {suites.map((suite) => (
            <SuiteCard key={suite.id} suite={suite} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <CreateSuiteModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreate}
      />
    </div>
  );
}
