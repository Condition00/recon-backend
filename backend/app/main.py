import logging
from contextlib import asynccontextmanager

import logfire
import redis.asyncio as redis
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.api import router
from app.utils.rbac import ensure_default_roles_and_admins
from app.core.config import settings
from app.db.database import AsyncSessionLocal, engine, get_db

logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    environment=settings.LOGFIRE_ENVIRONMENT,
    console={"span_style": "simple"}
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm up DB pool, initialize Redis. Shutdown: clean up."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        async with AsyncSessionLocal() as session:
            await ensure_default_roles_and_admins(session)
            await session.commit()
        app.state.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logfire.info("App started with database and Redis connections.")
    except Exception as e:
        logfire.error("Failed to initialize connections", exc_info=e)
        raise
    
    yield

    try:
        if hasattr(app.state, "redis"):
            await app.state.redis.aclose()
        await engine.dispose()
        logfire.info("App shutdown successfully.")
    except Exception as e:
        logfire.error("Error during shutdown", exc_info=e)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Instrument the app
logfire.instrument_fastapi(app=app)
logfire.instrument_asyncpg()
try:
    logfire.instrument_pydantic_ai()
except Exception:
    logger.warning("pydantic_ai not found, skipping instrumentation.")
logfire.instrument_redis()


# ── Global Exception Handler (ensures 500s return JSON through CORS) ──

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Middleware ────────────────────────────────────────────────

# SessionMiddleware — required for Authlib OAuth state storage
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS
ALLOWED_ORIGINS = [
    # Development
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    # Production
    "https://traction-ai.me",
    "https://www.traction-ai.me",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────

app.include_router(router, prefix=settings.API_V1_STR)


# ── Health / Root ─────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Welcome to the Traction API"}


@app.get("/db_check")
async def db_check(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }
