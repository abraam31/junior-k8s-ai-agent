"""FastAPI /ask endpoint for Junior will go here."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from .agent import answer, init
from .models import AskRequest, AskResponse
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init()
    yield 

FALLBACK_NAMESPACE = "sandbox"
app = FastAPI(title="Junior API", description="API for AI Junior Agent Chatbot", lifespan=lifespan)


@app.get("/health")
def health_check():
    """ Liveness and Readiness Probe Check """
    from .agent import _client, _api_client 
    if _client is None or _api_client is None:
        return {"status": "unhealthy"}, 503
    return {"status": "healthy"}, 200

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """ Placeholder for the ask endpoint """
    result = answer(req.question)
    body = {
        "question": req.question,
        "diagnosis": result.get("diagnosis", []),
        "summary": result.get("summary"),
        "error": result.get("error", None),
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "version": os.getenv("VERSION", "0.0.1"),
        "token_usage": result.get("token_usage", {"input": 0, "output": 0}),
    }
    if body["error"]:
        return JSONResponse(status_code=503, content=body)
    
    return body
