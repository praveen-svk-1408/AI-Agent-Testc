import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Test Suites API
export const testSuitesAPI = {
  getAll: () => apiClient.get('/test-suites'),
  getById: (id) => apiClient.get(`/test-suites/${id}`),
  create: (data) => apiClient.post('/test-suites', data),
  update: (id, data) => apiClient.put(`/test-suites/${id}`, data),
  delete: (id) => apiClient.delete(`/test-suites/${id}`),
};

// Test Cases API
export const testCasesAPI = {
  getAll: (suiteId) => apiClient.get(`/test-cases${suiteId ? `?suite_id=${suiteId}` : ''}`),
  getById: (id) => apiClient.get(`/test-cases/${id}`),
  create: (data) => apiClient.post('/test-cases', data),
  update: (id, data) => apiClient.put(`/test-cases/${id}`, data),
  delete: (id) => apiClient.delete(`/test-cases/${id}`),
};

// Test Steps API
export const testStepsAPI = {
  getAll: () => apiClient.get('/test-steps'),
  getById: (id) => apiClient.get(`/test-steps/${id}`),
  create: (data) => apiClient.post('/test-steps', data),
  update: (id, data) => apiClient.put(`/test-steps/${id}`, data),
  delete: (id) => apiClient.delete(`/test-steps/${id}`),
};

// Execution API
export const executionAPI = {
  runTestCase: (id) => apiClient.post(`/execution/test-cases/${id}/run`),
  runTestSuite: (id) => apiClient.post(`/execution/test-suites/${id}/run`),
  getResults: (id) => apiClient.get(`/execution/results/${id}`),
};

// Health Check
export const healthAPI = {
  check: () => apiClient.get('/health'),
};

export default apiClient;
