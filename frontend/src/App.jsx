import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import TestSuites from './pages/TestSuites';
import TestCases from './pages/TestCases';
import Execute from './pages/Execute';
import './styles/index.css';

export default function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/test-suites" element={<TestSuites />} />
        <Route path="/test-cases" element={<TestCases />} />
        <Route path="/execute" element={<Execute />} />
      </Routes>
    </Router>
  );
}
