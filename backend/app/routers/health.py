from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "AI-Agent Testing Platform"}


@router.get("/health/ollama")
async def ollama_health():
    """Check Ollama service health."""
    # TODO: Implement Ollama health check
    return {"status": "unknown", "service": "Ollama"}
