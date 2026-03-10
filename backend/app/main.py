from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_all_tables
from app.routers import test_suites, test_cases, test_steps, execution, generation, health
from app.utils.logger import logger

# Create all database tables
create_all_tables()

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI-driven UI Testing Platform - Generate and execute automated test cases using LLM",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(test_suites.router)
app.include_router(test_cases.router)
app.include_router(test_steps.router)
app.include_router(execution.router)
app.include_router(generation.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting AI-Agent Testing Platform")
    logger.info(f"API running at: {settings.API_TITLE}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down AI-Agent Testing Platform")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to AI-Agent Testing Platform",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
