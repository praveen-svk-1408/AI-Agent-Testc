import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path ? 'active' : '';

  return (
    <nav className="navbar">
      <div className="navbar-content">
        <Link to="/" className="navbar-brand">
          🤖 AI Testing Platform
        </Link>
        <ul className="navbar-links">
          <li>
            <Link to="/" className={isActive('/')}>
              Dashboard
            </Link>
          </li>
          <li>
            <Link to="/test-suites" className={isActive('/test-suites')}>
              Test Suites
            </Link>
          </li>
          <li>
            <Link to="/test-cases" className={isActive('/test-cases')}>
              Test Cases
            </Link>
          </li>
          <li>
            <Link to="/execute" className={isActive('/execute')}>
              Execute
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}
