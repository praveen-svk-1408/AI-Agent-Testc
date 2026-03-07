# AI-Agent UI Testing Platform - Frontend

A modern React-based frontend for the AI-Agent UI Testing Platform. Built with Vite, React Router, and Axios.

## Features

- **Dashboard**: Overview of test suites, cases, and API health status
- **Test Suites Management**: Create, view, and manage test suites
- **Test Cases Management**: Create and organize test cases within suites
- **Test Execution**: Run individual test cases or entire test suites
- **Results Viewer**: View execution results with detailed output
- **Responsive Design**: Works great on desktop, tablet, and mobile devices

## Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on http://localhost:8000

## Quick Start

### Option 1: Automatic Setup (Windows)

```bash
cd frontend
start.bat
```

### Option 2: Manual Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at: `http://localhost:3000`

## Building for Production

```bash
npm run build
npm run preview
```

This creates an optimized build in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/       # React components (Navbar)
│   ├── pages/           # Page components (Dashboard, TestSuites, etc.)
│   ├── services/        # API client service
│   ├── styles/          # Global CSS styles
│   ├── App.jsx          # Main app component with routing
│   └── main.jsx         # Entry point
├── public/              # Static assets
├── index.html           # HTML entry point
├── vite.config.js       # Vite configuration
├── package.json         # Dependencies
└── README.md            # This file
```

## Available Pages

### Dashboard
- Overview of total test suites and cases
- API health status
- Quick links to documentation
- Getting started guide

### Test Suites
- Create new test suites
- View all test suites with base URLs
- Delete test suites
- Quick access to test cases in each suite

### Test Cases
- Create test cases within suites
- View test steps for each case
- Expandable interface to see step details
- Delete test cases

### Execute
- Run individual test cases or entire suites
- Select test suite and case
- View execution results with status
- See execution time and output logs

## API Integration

The frontend communicates with the backend API at `http://localhost:8000/api`:

- **Test Suites**: GET, POST, PUT, DELETE `/test-suites`
- **Test Cases**: GET, POST, PUT, DELETE `/test-cases`
- **Test Steps**: GET, POST, PUT, DELETE `/test-steps`
- **Execution**: POST `/execution/test-cases/{id}/run`, POST `/execution/test-suites/{id}/run`
- **Health**: GET `/health`

## Technologies Used

- **React 18**: UI library
- **React Router v6**: Client-side routing
- **Vite**: Fast build tool and dev server
- **Axios**: HTTP client for API requests
- **CSS3**: Responsive styling with modern design

## Development

### Running Tests
```bash
npm test
```

### Code Formatting
```bash
npm run format
```

### Linting
```bash
npm run lint
```

## Styling

The frontend uses custom CSS with:
- Modern color palette (purple/indigo theme)
- Responsive grid layout
- Mobile-first design approach
- Smooth transitions and animations
- Accessibility considerations

### CSS Classes
- `.card`: Card container
- `.btn`: Button styles (primary, success, danger, secondary)
- `.form-control`: Form inputs and textarea
- `.table`: Table styling
- `.alert`: Alert/notification boxes
- `.badge`: Status badges
- `.steps-list`: Test steps display

## Environment Configuration

By default, the frontend connects to the backend at:
- `http://localhost:8000/api`

To change this, update the `API_BASE_URL` in `src/services/api.js`.

## Troubleshooting

### Backend API not responding
- Make sure the backend server is running on port 8000
- Check that CORS is enabled on the backend
- Look at the browser console for network errors

### Port 3000 already in use
- Kill the process using port 3000 or use a different port
- Update `vite.config.js` to use a different port

### Dependencies installation fails
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Try `npm install --legacy-peer-deps` if issues persist

## License

MIT

## Support

For issues or feature requests, please open an issue on the main project repository.
