import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import test_suites, test_cases, test_runs, generation, site_crawl
from app.services.ws_manager import manager as ws_manager

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent Test Platform",
        description="Multi-agent LLM-powered platform for generating Playwright test suites",
        version="0.1.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(test_suites.router)
    app.include_router(test_cases.router)
    app.include_router(test_runs.router)
    app.include_router(generation.router)
    app.include_router(site_crawl.router)

    # WebSocket endpoint for live test run updates
    @app.websocket("/ws/test-runs/{run_id}")
    async def test_run_websocket(websocket: WebSocket, run_id: str):
        await ws_manager.connect(run_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(run_id, websocket)

    # WebSocket endpoint for live site crawl progress
    @app.websocket("/ws/crawl/{suite_id}")
    async def crawl_websocket(websocket: WebSocket, suite_id: str):
        await ws_manager.connect(suite_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(suite_id, websocket)

    # Serve artifact files as static content
    artifacts_dir = os.path.abspath(settings.artifacts_dir)
    os.makedirs(artifacts_dir, exist_ok=True)
    app.mount(
        "/artifacts",
        StaticFiles(directory=artifacts_dir),
        name="artifacts",
    )

    @app.get("/api/settings")
    async def get_app_settings():
        return {
            "ollama_model": settings.ollama_model,
            "llm_temperature": settings.llm_temperature,
            "ollama_base_url": settings.ollama_base_url,
            "step_timeout_ms": settings.step_timeout_ms,
            "navigation_timeout_ms": settings.navigation_timeout_ms,
            "execution_timeout_s": settings.execution_timeout_s,
            "max_reverification_attempts": settings.max_reverification_attempts,
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}

    return app


app = create_app()
