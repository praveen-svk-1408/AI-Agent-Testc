import React, { useState, useEffect } from 'react';
import { testSuitesAPI } from '../services/api';

export default function TestSuites() {
  const [suites, setSuites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    base_url: '',
    description: '',
  });

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

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await testSuitesAPI.create(formData);
      setFormData({ name: '', base_url: '', description: '' });
      setShowForm(false);
      fetchSuites();
    } catch (err) {
      setError('Failed to create test suite');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this test suite?')) {
      try {
        await testSuitesAPI.delete(id);
        fetchSuites();
      } catch (err) {
        setError('Failed to delete test suite');
      }
    }
  };

  return (
    <div className="container">
      <div className="main-content">
        <div className="card">
          <div className="card-header">
            <h1 className="card-title">Test Suites</h1>
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
              {showForm ? '✕ Cancel' : '+ New Suite'}
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
              <h3 style={{ marginBottom: '1rem' }}>Create New Test Suite</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label className="form-label">Suite Name *</label>
                  <input
                    type="text"
                    name="name"
                    className="form-control"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="e.g., E-commerce site"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Base URL *</label>
                  <input
                    type="url"
                    name="base_url"
                    className="form-control"
                    value={formData.base_url}
                    onChange={handleInputChange}
                    placeholder="e.g., http://localhost:3000"
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
                    placeholder="Describe the purpose of this test suite"
                  />
                </div>

                <button type="submit" className="btn btn-success">
                  ✓ Create Suite
                </button>
              </form>
            </div>
          )}

          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              <p>Loading test suites...</p>
            </div>
          ) : suites.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📦</div>
              <div className="empty-state-title">No Test Suites Yet</div>
              <p>Create your first test suite to get started</p>
            </div>
          ) : (
            <div className="grid grid-2">
              {suites.map(suite => (
                <div key={suite.id} className="card" style={{ border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
                    <h3 style={{ color: '#2d3748' }}>{suite.name}</h3>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(suite.id)}
                    >
                      🗑️ Delete
                    </button>
                  </div>
                  <p style={{ color: '#718096', marginBottom: '0.5rem' }}>
                    <strong>Base URL:</strong> {suite.base_url}
                  </p>
                  <p style={{ color: '#718096', marginBottom: '1rem', minHeight: '3rem' }}>
                    <strong>Description:</strong> {suite.description || 'N/A'}
                  </p>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                    <a href={`/test-cases?suite=${suite.id}`} className="btn btn-primary btn-sm">
                      📋 View Cases
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
