"""FraudGuard API entry point."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import analytics, auth, documents, extraction, fraud, health, rules, vendors

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("fraudguard")

app = FastAPI(
    title="FraudGuard API",
    description="Vendor invoice fraud detection for Indian SMBs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last line of defence — no raw stack traces reach the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again."},
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(fraud.router)
app.include_router(vendors.router)
app.include_router(rules.router)
app.include_router(analytics.router)


@app.on_event("startup")
def startup():
    # Ensure the storage bucket exists so first upload never fails
    try:
        from app.services.storage import storage_service

        storage_service.ensure_bucket()
    except Exception:
        logger.warning("Could not ensure MinIO bucket at startup", exc_info=True)
