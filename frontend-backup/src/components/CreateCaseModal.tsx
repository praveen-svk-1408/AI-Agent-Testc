"use client";

import { useState, type FormEvent } from "react";
import type { CreateTestCaseRequest, TestType } from "@/types";

const TEST_TYPES: { value: TestType; label: string; desc: string }[] = [
  { value: "functional", label: "Functional", desc: "Individual feature behavior" },
  { value: "e2e", label: "End-to-End", desc: "Complete user journeys" },
  { value: "integration", label: "Integration", desc: "Component interactions" },
  { value: "accessibility", label: "Accessibility", desc: "WCAG compliance" },
  { value: "visual", label: "Visual", desc: "Layout & appearance" },
  { value: "performance", label: "Performance", desc: "Load times & responsiveness" },
];

interface CreateCaseModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CreateTestCaseRequest) => Promise<void>;
}

export default function CreateCaseModal({ open, onClose, onSubmit }: CreateCaseModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [testType, setTestType] = useState<TestType>("functional");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ title, description, test_type: testType });
      setTitle("");
      setDescription("");
      setTestType("functional");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create test case");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Create Test Case</h2>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:text-gray-600">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Title *</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g., User can add product to cart"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Test Description (natural language) *
            </label>
            <textarea
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Describe the test scenario in plain English. The AI will analyze this and generate Playwright test steps.&#10;&#10;Example: Navigate to the home page, search for 'laptop', click on the first product, add it to the cart, go to the cart page, and verify the product appears with the correct price."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Test Type *</label>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {TEST_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setTestType(t.value)}
                  className={`rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                    testType === t.value
                      ? "border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-500"
                      : "border-gray-300 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <div className="font-medium">{t.label}</div>
                  <div className="text-xs text-gray-500">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Creating..." : "Create Test Case"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
