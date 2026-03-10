"use client";

import { useState, useEffect, useCallback } from "react";
import * as api from "@/services/api";
import type { TestSuite, TestSuiteDetail, CreateTestSuiteRequest } from "@/types";

export function useTestSuites() {
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSuites = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getTestSuites();
      setSuites(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch suites");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSuites();
  }, [fetchSuites]);

  const create = async (data: CreateTestSuiteRequest) => {
    const suite = await api.createTestSuite(data);
    setSuites((prev) => [suite, ...prev]);
    return suite;
  };

  const remove = async (id: string) => {
    await api.deleteTestSuite(id);
    setSuites((prev) => prev.filter((s) => s.id !== id));
  };

  return { suites, loading, error, refetch: fetchSuites, create, remove };
}

export function useTestSuite(id: string) {
  const [suite, setSuite] = useState<TestSuiteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSuite = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getTestSuite(id);
      setSuite(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch suite");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSuite();
  }, [fetchSuite]);

  return { suite, loading, error, refetch: fetchSuite };
}
