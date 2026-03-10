import { API_BASE_URL } from "@/lib/constants";
import type {
  TestSuite,
  TestSuiteDetail,
  TestCase,
  TestCaseDetail,
  TestRun,
  TestRunDetail,
  CreateTestSuiteRequest,
  CreateTestCaseRequest,
  CreateTestRunRequest,
  UpdateTestStepData,
} from "@/types";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Test Suites
export async function getTestSuites(): Promise<TestSuite[]> {
  return request<TestSuite[]>("/test-suites");
}

export async function getTestSuite(id: string): Promise<TestSuiteDetail> {
  return request<TestSuiteDetail>(`/test-suites/${id}`);
}

export async function createTestSuite(
  data: CreateTestSuiteRequest
): Promise<TestSuite> {
  return request<TestSuite>("/test-suites", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTestSuite(
  id: string,
  data: Partial<CreateTestSuiteRequest>
): Promise<TestSuite> {
  return request<TestSuite>(`/test-suites/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTestSuite(id: string): Promise<void> {
  return request<void>(`/test-suites/${id}`, { method: "DELETE" });
}

// Test Cases
export async function getTestCases(suiteId: string): Promise<TestCase[]> {
  return request<TestCase[]>(`/test-suites/${suiteId}/test-cases`);
}

export async function getTestCase(caseId: string): Promise<TestCaseDetail> {
  return request<TestCaseDetail>(`/test-cases/${caseId}`);
}

export async function createTestCase(
  suiteId: string,
  data: CreateTestCaseRequest
): Promise<TestCase> {
  return request<TestCase>(`/test-suites/${suiteId}/test-cases`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteTestCase(caseId: string): Promise<void> {
  return request<void>(`/test-cases/${caseId}`, { method: "DELETE" });
}

export async function updateTestSteps(
  caseId: string,
  steps: UpdateTestStepData[]
): Promise<TestCaseDetail> {
  return request<TestCaseDetail>(`/test-cases/${caseId}/steps`, {
    method: "PUT",
    body: JSON.stringify({ steps }),
  });
}

// Generation
export async function triggerGeneration(
  caseId: string
): Promise<{ message: string; case_id: string; status: string; attempt: number }> {
  return request(`/test-cases/${caseId}/generate`, { method: "POST" });
}

export async function getGenerationStatus(
  caseId: string
): Promise<{
  case_id: string;
  case_status: string;
  generation: {
    status: string;
    progress: string[];
    error: string | null;
    steps_count?: number;
  } | null;
}> {
  return request(`/test-cases/${caseId}/generate/status`);
}

// Test Runs
export async function getTestRuns(caseId?: string): Promise<TestRun[]> {
  const params = caseId ? `?case_id=${caseId}` : "";
  return request<TestRun[]>(`/test-runs${params}`);
}

export async function getTestRun(runId: string): Promise<TestRunDetail> {
  return request<TestRunDetail>(`/test-runs/${runId}`);
}

export async function createTestRun(
  data: CreateTestRunRequest
): Promise<TestRun> {
  return request<TestRun>("/test-runs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Artifacts
export function getArtifactDownloadUrl(runId: string, artifactId: string): string {
  return `${API_BASE_URL}/test-runs/${runId}/artifacts/${artifactId}/download`;
}
