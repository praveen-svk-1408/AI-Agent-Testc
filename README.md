# AI-Agent UI Testing Platform

An intelligent, LLM-driven UI testing platform that automatically generates test cases and executes them against web applications.

## Features

- **Smart Test Generation**: Use Ollama LLaMA to intelligently generate test cases from URL context
- **Test Management**: Organize tests into suites and cases with detailed execution steps
- **Browser Automation**: Execute tests using Playwright with full control and reporting
- **Result Tracking**: Store and analyze test execution results with screenshots and logs
- **RESTful API**: Complete API for test management and execution

## Architecture

```
Frontend (React + TypeScript)
        ↓
FastAPI Backend
        ↓
├── PostgreSQL Database
├── Ollama LLM Service (Test Generation)
└── Playwright Runner (Test Execution)
```

## Project Structure

```
AI-Agent-Testc/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routers/           # API endpoints
│   │   ├── services/          # Business logic (LLM, crawler, executor)
│   │   ├── runners/           # Playwright test execution
│   │   ├── utils/             # Utilities and helpers
│   │   ├── main.py            # FastAPI application
│   │   ├── config.py          # Configuration
│   │   └── database.py        # Database setup
│   ├── scripts/               # Utility scripts (init_db.py)
│   ├── tests/                 # Unit tests
│   ├── requirements.txt        # Python dependencies
│   └── .env.example           # Environment variables template
├── frontend/                   # React TypeScript frontend (coming soon)
├── playwright-runners/         # Generated test scripts
├── docker-compose.yml         # Docker services (PostgreSQL, Ollama)
└── README.md

```

## Backend Implementation

### Database Models

- **TestSuite**: Contains base URL and multiple test cases
- **TestCase**: Individual test cases under a suite (e.g., /login, /products)
- **TestStep**: Individual steps in a test (navigate, click, fill, assert)
- **ExecutionResult**: Results from running a test case

### API Endpoints

#### Test Suites
- `POST /api/test-suites` - Create suite
- `GET /api/test-suites` - List suites
- `GET /api/test-suites/{id}` - Get suite details
- `PUT /api/test-suites/{id}` - Update suite
- `DELETE /api/test-suites/{id}` - Delete suite

#### Test Cases
- `POST /api/test-cases` - Create test case
- `GET /api/test-cases` - List test cases
- `GET /api/test-cases/{id}` - Get test case with steps
- `PUT /api/test-cases/{id}` - Update test case
- `DELETE /api/test-cases/{id}` - Delete test case

#### Test Steps
- `POST /api/test-steps` - Create step
- `GET /api/test-steps` - List steps
- `GET /api/test-steps/{id}` - Get step details
- `PUT /api/test-steps/{id}` - Update step
- `DELETE /api/test-steps/{id}` - Delete step

#### Test Generation & Execution
- `POST /api/generate-tests` - Generate tests using LLM
- `POST /api/execution/test-cases/{id}/run` - Run single test
- `POST /api/execution/test-suites/{id}/run` - Run suite
- `GET /api/execution/results/{id}` - Get execution results
- `GET /api/health` - Health check

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL 14+ (optional, for production)
- Docker & Docker Compose (optional, for Ollama)

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create Python virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional):
   ```bash
   cp .env.example .env
   ```
   The default SQLite database will be created automatically.

5. **Initialize database**:
   ```bash
   python scripts/init_db.py
   ```

6. **Run FastAPI server**:
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

### Using Docker Compose (Optional for Ollama LLM)

To use Ollama for test generation, start it with Docker:
```bash
docker-compose up -d ollama
docker exec ai-test-ollama ollama pull llama2
```

For production with PostgreSQL database:
```bash
docker-compose up -d postgres
```

View logs:
```bash
docker-compose logs -f
```

Stop all services:
```bash
docker-compose down
```

## API Examples

### Create a Test Suite

```bash
curl -X POST http://localhost:8000/api/test-suites \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Login Tests",
    "base_url": "http://localhost:3000",
    "description": "Test cases for login functionality"
  }'
```

### Create a Test Case

```bash
curl -X POST http://localhost:8000/api/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "suite_id": 1,
    "path": "/login",
    "name": "Successful Login",
    "description": "Test successful login with valid credentials"
  }'
```

### Create a Test Step

```bash
curl -X POST http://localhost:8000/api/test-steps \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": 1,
    "action_type": "navigate",
    "value": "http://localhost:3000/login",
    "order": 1,
    "description": "Navigate to login page"
  }'
```

### Check Health

```bash
curl http://localhost:8000/api/health
```

## Next Steps

- [ ] Implement Ollama LLM integration for test generation
- [ ] Implement Playwright test executor
- [ ] Create frontend React application
- [ ] Add WebSocket support for live test execution
- [ ] Implement screenshot capture and storage
- [ ] Add test result reporting and visualization
- [ ] Set up authentication and authorization
- [ ] Add test scheduling and CI/CD integration

## Sample E-Commerce Application

A complete sample e-commerce web application is included in the `sample-ecommerce` directory to help you test and develop your UI testing platform. It includes:

- **Backend:** Node.js/Express REST API with authentication, products, cart, and orders
- **Frontend:** React with responsive UI for browsing products, managing carts, and placing orders
- **In-Memory Database:** Pre-populated with sample products and users
- **Ready-to-Test Pages:** Login, product listing, product details, shopping cart, checkout, order history

### Quick Start Sample App

```bash
cd sample-ecommerce

# Windows
start-app.bat

# Linux/Mac
chmod +x start-app.sh
./start-app.sh
```

Or manually:
```bash
# Terminal 1 - Backend
cd sample-ecommerce/backend
npm install
npm start

# Terminal 2 - Frontend
cd sample-ecommerce/frontend
npm install
npm start
```

**Frontend:** http://localhost:3000
**Backend:** http://localhost:5000

**Test Credentials:** 
- Email: test@example.com
- Password: password123

See [sample-ecommerce/README.md](sample-ecommerce/README.md) for more details.

## Development

### Run Tests
```bash
pytest tests/
```

### Format Code
```bash
black app/
isort app/
```

### Type Checking
```bash
mypy app/
```

## Technologies

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL
- **LLM**: Ollama (LLaMA 2)
- **Browser Automation**: Playwright
- **Frontend** (coming): React, TypeScript, Redux
- **Deployment**: Docker, Docker Compose

## License

MIT

## Support

For issues and feature requests, please open an issue on GitHub.