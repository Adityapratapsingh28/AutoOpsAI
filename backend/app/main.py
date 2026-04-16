"""
AutoOps AI — FastAPI Application Entry Point.

The main server that ties together all routes, middleware, and startup
hooks. Serves both the API and the static frontend files.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.database import get_pool, close_pool
from .routes.auth import router as auth_router
from .routes.workflow import router as workflow_router
from .routes.dashboard import router as dashboard_router
from .routes.files import router as files_router
from .routes.meetings import router as meetings_router
from .routes.manager import router as manager_router
from .routes.governance import router as governance_router

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("autoops.main")


# ── Lifespan (startup / shutdown) ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AutoOps AI starting up...")
    await get_pool()
    logger.info("✅ Database pool ready")
    yield
    logger.info("🛑 AutoOps AI shutting down...")
    await close_pool()


# ── FastAPI App ──
app = FastAPI(
    title="AutoOps AI",
    description="Enterprise-grade Multi-Agent AI Workflow Automation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.responses import JSONResponse

# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Uncaught exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal System Error - Try again."},
        headers={"Access-Control-Allow-Origin": "*"}
    )

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ──
app.include_router(auth_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(meetings_router, prefix="/api")
app.include_router(manager_router, prefix="/api")
app.include_router(governance_router, prefix="/api")


# ── Health Check ──
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AutoOps AI",
        "version": "1.0.0",
    }


# ── Dev Route: Simulate Crash ──
@app.get("/api/dev/crash")
async def trigger_crash():
    logger.info("Intentionally triggering a crash for demonstration...")
    # This will throw a ZeroDivisionError
    1 / 0
    return {"message": "You will never see this"}


# ── Serve Frontend Static Files ──
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info(f"Serving frontend from: {frontend_dir}")
