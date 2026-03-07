import React, { useState, useEffect } from 'react';
import { testSuitesAPI, testCasesAPI, healthAPI } from '../services/api';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalSuites: 0,
    totalCases: 0,
    healthStatus: 'checking',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [suitesRes, casesRes, healthRes] = await Promise.all([
        testSuitesAPI.getAll(),
        testCasesAPI.getAll(),
        healthAPI.check(),
      ]);

      setStats({
        totalSuites: suitesRes.data.length,
        totalCases: casesRes.data.length,
        healthStatus: healthRes.data.status === 'healthy' ? 'healthy' : 'unhealthy',
      });
    } catch (err) {
      setError(err.message);
      setStats({
        totalSuites: 0,
        totalCases: 0,
        healthStatus: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="main-content">
        <div className="card">
          <div className="card-header">
            <h1 className="card-title">Dashboard</h1>
            <button className="btn btn-primary" onClick={fetchData}>
              🔄 Refresh
            </button>
          </div>

          {error && (
            <div className="alert alert-error">
              ⚠️ {error}
            </div>
          )}

          <div className="grid grid-3">
            <div className="card">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📦</div>
                <h3 style={{ color: '#2d3748', marginBottom: '0.5rem' }}>Test Suites</h3>
                <p style={{ fontSize: '2rem', color: '#667eea', fontWeight: 'bold' }}>
                  {loading ? '...' : stats.totalSuites}
                </p>
              </div>
            </div>

            <div className="card">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🧪</div>
                <h3 style={{ color: '#2d3748', marginBottom: '0.5rem' }}>Test Cases</h3>
                <p style={{ fontSize: '2rem', color: '#667eea', fontWeight: 'bold' }}>
                  {loading ? '...' : stats.totalCases}
                </p>
              </div>
            </div>

            <div className="card">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
                  {stats.healthStatus === 'healthy' ? '✅' : stats.healthStatus === 'error' ? '❌' : '⏳'}
                </div>
                <h3 style={{ color: '#2d3748', marginBottom: '0.5rem' }}>API Status</h3>
                <p style={{ 
                  fontSize: '1rem', 
                  fontWeight: 'bold',
                  color: stats.healthStatus === 'healthy' ? '#48bb78' : '#f56565'
                }}>
                  {stats.healthStatus.toUpperCase()}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">Getting Started</h2>
          <p style={{ marginBottom: '1rem', color: '#718096' }}>
            Welcome to the AI-Agent UI Testing Platform! Here's how to get started:
          </p>
          <ol style={{ marginLeft: '2rem', color: '#718096', lineHeight: '1.8' }}>
            <li>Create a <strong>Test Suite</strong> for your application</li>
            <li>Add <strong>Test Cases</strong> within the suite</li>
            <li>Define <strong>Test Steps</strong> for each test case</li>
            <li><strong>Execute</strong> tests to validate your application</li>
            <li>View and analyze <strong>Results</strong></li>
          </ol>
        </div>

        <div className="card">
          <h2 className="card-title">API Documentation</h2>
          <p style={{ marginBottom: '1rem', color: '#718096' }}>
            Access the interactive API documentation:
          </p>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="btn btn-primary">
              📚 Swagger UI
            </a>
            <a href="http://localhost:8000/redoc" target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
              📖 ReDoc
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
