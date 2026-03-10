import { useState, useEffect } from 'react';
import { testSuitesAPI, testCasesAPI, executionAPI } from '../services/api';

export default function Execute() {
  const [suites, setSuites] = useState([]);
  const [cases, setCases] = useState([]);
  const [selectedSuite, setSelectedSuite] = useState('');
  const [selectedCase, setSelectedCase] = useState('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSuites();
  }, []);

  const fetchSuites = async () => {
    try {
      setLoading(true);
      const response = await testSuitesAPI.getAll();
      setSuites(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load test suites');
      setSuites([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuiteChange = async (e) => {
    const suiteId = e.target.value;
    setSelectedSuite(suiteId);
    setSelectedCase('');

    if (suiteId) {
      try {
        const response = await testCasesAPI.getAll(suiteId);
        setCases(response.data);
      } catch (err) {
        setError('Failed to load test cases');
        setCases([]);
      }
    } else {
      setCases([]);
    }
  };

  const handleExecuteTestSuite = async () => {
    if (!selectedSuite) {
      setError('Please select a test suite');
      return;
    }

    try {
      setExecuting(true);
      const response = await executionAPI.runTestSuite(selectedSuite);
      setResult({
        type: 'suite',
        data: response.data,
      });
    } catch (err) {
      setError('Failed to execute test suite: ' + err.message);
    } finally {
      setExecuting(false);
    }
  };

  const handleExecuteTestCase = async () => {
    if (!selectedCase) {
      setError('Please select a test case');
      return;
    }

    try {
      setExecuting(true);
      const response = await executionAPI.runTestCase(selectedCase);
      setResult({
        type: 'case',
        data: response.data,
      });
    } catch (err) {
      setError('Failed to execute test case: ' + err.message);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="container">
      <div className="main-content">
        <div className="card">
          <div className="card-header">
            <h1 className="card-title">Execute Tests</h1>
          </div>

          {error && (
            <div className="alert alert-error">
              ⚠️ {error}
              <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}>
                ✕
              </button>
            </div>
          )}

          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              <p>Loading test suites...</p>
            </div>
          ) : (
            <div>
              <div style={{ background: '#f7fafc', padding: '1.5rem', borderRadius: '4px', marginBottom: '2rem' }}>
                <div className="form-group">
                  <label className="form-label">Select Test Suite *</label>
                  <select
                    className="form-control"
                    value={selectedSuite}
                    onChange={handleSuiteChange}
                  >
                    <option value="">Choose a suite...</option>
                    {suites.map(suite => (
                      <option key={suite.id} value={suite.id}>
                        {suite.name} ({suite.base_url})
                      </option>
                    ))}
                  </select>
                </div>

                {selectedSuite && (
                  <>
                    <div className="form-group">
                      <label className="form-label">Or Select Test Case</label>
                      <select
                        className="form-control"
                        value={selectedCase}
                        onChange={(e) => setSelectedCase(e.target.value)}
                      >
                        <option value="">Run entire suite...</option>
                        {cases.map(testCase => (
                          <option key={testCase.id} value={testCase.id}>
                            {testCase.name} ({testCase.path})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem' }}>
                      <button
                        className="btn btn-success"
                        onClick={handleExecuteTestSuite}
                        disabled={executing}
                      >
                        {executing ? '⏳ Executing...' : '▶️ Run Suite'}
                      </button>
                      {selectedCase && (
                        <button
                          className="btn btn-primary"
                          onClick={handleExecuteTestCase}
                          disabled={executing}
                        >
                          {executing ? '⏳ Executing...' : '▶️ Run Case'}
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>

              {result && (
                <div className="card" style={{ border: `2px solid ${result.data.status === 'passed' ? '#48bb78' : '#f56565'}` }}>
                  <div className="card-header">
                    <h2 className="card-title">Execution Results</h2>
                    <span className={`badge ${result.data.status === 'passed' ? 'badge-success' : 'badge-danger'}`}>
                      {result.data.status?.toUpperCase()}
                    </span>
                  </div>

                  <div style={{ marginBottom: '1.5rem' }}>
                    <p><strong>Type:</strong> {result.type === 'suite' ? 'Test Suite' : 'Test Case'}</p>
                    {result.data.output && (
                      <div style={{ marginTop: '1rem' }}>
                        <strong>Output:</strong>
                        <pre style={{
                          background: '#f7fafc',
                          padding: '1rem',
                          borderRadius: '4px',
                          overflow: 'auto',
                          maxHeight: '300px',
                          marginTop: '0.5rem',
                        }}>
                          {result.data.output}
                        </pre>
                      </div>
                    )}
                    {result.data.execution_time && (
                      <p style={{ marginTop: '1rem' }}>
                        <strong>Execution Time:</strong> {result.data.execution_time.toFixed(2)}s
                      </p>
                    )}
                  </div>

                  <button className="btn btn-secondary" onClick={() => setResult(null)}>
                    ✕ Clear Results
                  </button>
                </div>
              )}

              {!result && (
                <div className="card">
                  <div className="card-title" style={{ marginBottom: '1rem' }}>📋 How to Execute Tests</div>
                  <ol style={{ color: '#718096', lineHeight: '1.8' }}>
                    <li>Select a <strong>Test Suite</strong> from the dropdown</li>
                    <li>Optionally select a specific <strong>Test Case</strong> to run</li>
                    <li>Click <strong>Run Suite</strong> to execute all cases or <strong>Run Case</strong> for a single case</li>
                    <li>Results will appear below with execution details</li>
                  </ol>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
