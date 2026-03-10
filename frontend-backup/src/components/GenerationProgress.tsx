"use client";

import { useState, useEffect, useRef } from "react";
import * as api from "@/services/api";

interface GenerationProgressProps {
  caseId: string;
  isGenerating: boolean;
  onComplete: () => void;
}

export default function GenerationProgress({
  caseId,
  isGenerating,
  onComplete,
}: GenerationProgressProps) {
  const [progress, setProgress] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [genStatus, setGenStatus] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isGenerating) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    setProgress(["Generation started..."]);
    setError(null);
    setGenStatus("running");

    const poll = async () => {
      try {
        const status = await api.getGenerationStatus(caseId);
        if (status.generation) {
          setProgress(status.generation.progress || []);
          setError(status.generation.error);
          setGenStatus(status.generation.status);

          if (
            status.generation.status === "success" ||
            status.generation.status === "failed" ||
            status.case_status === "generated" ||
            status.case_status === "failed"
          ) {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
            // Brief delay so the user can see the final message
            setTimeout(onComplete, 1000);
          }
        }
      } catch {
        // Polling error, continue
      }
    };

    // Start polling every 2 seconds
    intervalRef.current = setInterval(poll, 2000);
    // Also poll immediately
    poll();

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isGenerating, caseId, onComplete]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [progress]);

  if (!isGenerating && progress.length === 0) return null;

  const statusColor =
    genStatus === "success"
      ? "border-green-200 bg-green-50"
      : genStatus === "failed"
        ? "border-red-200 bg-red-50"
        : "border-blue-200 bg-blue-50";

  return (
    <div className={`mb-6 rounded-lg border ${statusColor} p-4`}>
      <div className="mb-2 flex items-center gap-2">
        {genStatus === "running" && (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        )}
        {genStatus === "success" && (
          <svg className="h-4 w-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
        {genStatus === "failed" && (
          <svg className="h-4 w-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
        <span className="text-sm font-medium text-gray-900">
          {genStatus === "running"
            ? "Generating test steps..."
            : genStatus === "success"
              ? "Generation complete"
              : "Generation failed"}
        </span>
      </div>

      <div className="max-h-48 overflow-y-auto rounded bg-white/60 p-3">
        {progress.map((msg, i) => (
          <div key={i} className="flex items-start gap-2 py-0.5 text-xs text-gray-700">
            <span className="mt-0.5 text-gray-400">{i + 1}.</span>
            <span>{msg}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && genStatus === "failed" && (
        <div className="mt-2 text-xs text-red-600">Error: {error}</div>
      )}
    </div>
  );
}
