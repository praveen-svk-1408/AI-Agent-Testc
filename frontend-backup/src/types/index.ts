// Domain types matching backend Pydantic schemas

export interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  base_url: string;
  app_description: string | null;
  created_at: string;
  updated_at: string;
  test_case_count: number;
}

export interface TestSuiteDetail extends TestSuite {
  test_cases: TestCase[];
}

export type TestType = "functional" | "e2e" | "integration" | "accessibility" | "visual" | "performance";

export interface TestCase {
  id: string;
  suite_id: string;
  title: string;
  description: string;
  test_type: TestType;
  status: "draft" | "generating" | "generated" | "failed";
  generation_attempts: number;
  created_at: string;
  updated_at: string;
}

export interface TestStep {
  id: string;
  order: number;
  action: string;
  selector: string | null;
  value: string | null;
  expected_result: string | null;
  description: string | null;
}

export interface TestCaseDetail extends TestCase {
  test_steps: TestStep[];
}

export interface TestRun {
  id: string;
  case_id: string;
  status: "pending" | "running" | "passed" | "failed" | "error";
  browser: "chromium" | "firefox" | "webkit";
  headed: boolean;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

export interface Artifact {
  id: string;
  run_id: string;
  artifact_type: "screenshot" | "video" | "trace" | "log";
  file_name: string;
  mime_type: string | null;
  file_size: number | null;
  created_at: string;
}

export interface TestRunDetail extends TestRun {
  result_summary: Record<string, unknown> | null;
  artifacts: Artifact[];
}

// Request types
export interface CreateTestSuiteRequest {
  name: string;
  description?: string;
  base_url: string;
  app_description?: string;
}

export interface CreateTestCaseRequest {
  title: string;
  description: string;
  test_type?: TestType;
}

export interface UpdateTestStepData {
  order: number;
  action: string;
  selector: string | null;
  value: string | null;
  expected_result: string | null;
  description: string | null;
}

export interface CreateTestRunRequest {
  case_id: string;
  browser?: "chromium" | "firefox" | "webkit";
  headed?: boolean;
}

// WebSocket event types
export interface WSStatusChange {
  event: "status_change";
  status: string;
  timestamp: string;
}

export interface WSTestStep {
  event: "test_step";
  step: string;
  screenshot_url?: string;
  screenshot_base64?: string;
  status?: string;
  order?: number;
  action?: string;
  duration_ms?: number;
  timestamp: string;
}

export interface WSArtifactReady {
  event: "artifact_ready";
  artifact: Artifact;
  timestamp: string;
}

export type WSEvent = WSStatusChange | WSTestStep | WSArtifactReady;
