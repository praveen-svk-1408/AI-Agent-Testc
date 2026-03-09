"use client";

import { useState, useEffect, useCallback } from "react";
import * as api from "@/services/api";
import type { TestRun, TestRunDetail } from "@/types";

export function useTestRuns(caseId?: string) {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getTestRuns(caseId);
      setRuns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch runs");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return { runs, loading, error, refetch: fetchRuns };
}

export function useTestRun(runId: string) {
  const [run, setRun] = useState<TestRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRun = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getTestRun(runId);
      setRun(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch run");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  return { run, loading, error, refetch: fetchRun };
}
