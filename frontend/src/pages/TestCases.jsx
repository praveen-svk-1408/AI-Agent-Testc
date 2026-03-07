import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { testCasesAPI, testSuitesAPI, testStepsAPI } from '../services/api';

export default function TestCases() {
  const [searchParams] = useSearchParams();
  const suiteId = searchParams.get('suite');

  const [cases, setCases] = useState([]);
  const [suites, setSuites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [expandedCase, setExpandedCase] = useState(null);
  const [formData, setFormData] = useState({
    suite_id: suiteId ? parseInt(suiteId) : '',
    path: '',
    name: '',
    description: '',
  });

  useEffect(() => {
    fetchData();
  }, [suiteId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [casesRes, suitesRes] = await Promise.all([
        testCasesAPI.getAll(suiteId),
        testSuitesAPI.getAll(),
      ]);
      setCases(casesRes.data);
      setSuites(suitesRes.data);
      setError(null);
    } catch (err) {
      setError('Failed to load test cases');
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'suite_id' ? parseInt(value) || '' : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await testCasesAPI.create(formData);
      setFormData({ suite_id: suiteId ? parseInt(suiteId) : '', path: '', name: '', description: '' });
      setShowForm(false);
      fetchData();
    } catch (err) {
      setError('Failed to create test case');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this test case?')) {
      try {
        await testCasesAPI.delete(id);
        fetchData();
      } catch (err) {
        setError('Failed to delete test case');
      }
    }
  };

  const toggleExpand = async (caseId) => {
    if (expandedCase === caseId) {
      setExpandedCase(null);
    } else {
      try {
        const response = await testCasesAPI.getById(caseId);
        setExpandedCase(caseId);
      } catch (err) {
        setError('Failed to load test steps');
      }
    }
  };

  return (
    <div className="container">
      <div className="main-content">
        <div className="card">
          <div className="card-header">
            <h1 className="card-title">Test Cases</h1>
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
              {showForm ? '✕ Cancel' : '+ New Case'}
            </button>
          </div>

          {error && (
            <div className="alert alert-error">
              ⚠️ {error}
              <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}>
                ✕
              </button>
            </div>
          )}

          {showForm && (
            <div style={{ background: '#f7fafc', padding: '1.5rem', borderRadius: '4px', marginBottom: '1.5rem' }}>
              <h3 style={{ marginBottom: '1rem' }}>Create New Test Case</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label className="form-label">Test Suite *</label>
                  <select
                    name="suite_id"
                    className="form-control"
                    value={formData.suite_id}
                    onChange={handleInputChange}
                    required
                  >
                    <option value="">Select a suite</option>
                    {suites.map(suite => (
                      <option key={suite.id} value={suite.id}>
                        {suite.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Test Case Name *</label>
                  <input
                    type="text"
                    name="name"
                    className="form-control"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="e.g., Test Login"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Path *</label>
                  <input
                    type="text"
                    name="path"
                    className="form-control"
                    value={formData.path}
                    onChange={handleInputChange}
                    placeholder="e.g., /login"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Description</label>
                  <textarea
                    name="description"
                    className="form-control"
                    value={formData.description}
                    onChange={handleInputChange}
                    placeholder="Describe what this test case does"
                  />
                </div>

                <button type="submit" className="btn btn-success">
                  ✓ Create Case
                </button>
              </form>
            </div>
          )}

          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              <p>Loading test cases...</p>
            </div>
          ) : cases.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🧪</div>
              <div className="empty-state-title">No Test Cases Yet</div>
              <p>Create your first test case to define test scenarios</p>
            </div>
          ) : (
            <div>
              {cases.map(testCase => (
                <div key={testCase.id} style={{ marginBottom: '1rem', border: '1px solid #e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                  <div
                    style={{
                      padding: '1.5rem',
                      background: '#f7fafc',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      cursor: 'pointer',
                    }}
                    onClick={() => toggleExpand(testCase.id)}
                  >
                    <div>
                      <h3 style={{ color: '#2d3748', marginBottom: '0.5rem' }}>
                        {testCase.name}
                      </h3>
                      <p style={{ color: '#718096', marginBottom: '0' }}>
                        Path: <code style={{ background: '#fff', padding: '2px 6px', borderRadius: '2px' }}>{testCase.path}</code>
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(testCase.id);
                        }}
                      >
                        🗑️ Delete
                      </button>
                      <span style={{ padding: '0.75rem', fontSize: '1.2rem' }}>
                        {expandedCase === testCase.id ? '▼' : '▶'}
                      </span>
                    </div>
                  </div>

                  {expandedCase === testCase.id && (
                    <div style={{ padding: '1.5rem', borderTop: '1px solid #e2e8f0' }}>
                      <p style={{ color: '#718096', marginBottom: '1rem' }}>
                        <strong>Description:</strong> {testCase.description || 'N/A'}
                      </p>
                      {testCase.steps && testCase.steps.length > 0 ? (
                        <div>
                          <h4 style={{ marginBottom: '1rem' }}>Test Steps ({testCase.steps.length})</h4>
                          <ul className="steps-list">
                            {testCase.steps.map(step => (
                              <li key={step.id} className="step-item">
                                <span className="step-number">{step.order}</span>
                                <div className="step-content">
                                  <div className="step-action">{step.action_type}</div>
                                  <div className="step-description">{step.description}</div>
                                  {step.target_selector && (
                                    <div style={{ color: '#666', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                      Selector: <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '2px' }}>{step.target_selector}</code>
                                    </div>
                                  )}
                                  {step.value && (
                                    <div style={{ color: '#666', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                      Value: <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '2px' }}>{step.value}</code>
                                    </div>
                                  )}
                                </div>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <p style={{ color: '#718096' }}>No test steps defined yet</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
