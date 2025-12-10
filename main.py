"""
WhatsApp Price Intelligence - Backend API
FastAPI application principale
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers import extraction_routes, prediction_routes, stats_routes, aliment_routes, aliment_prediction_routes
from db.database import engine, Base
from utils.config import settings
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    logger.info("🚀 Starting WhatsApp Price Intelligence API")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("🛑 Shutting down API")


app = FastAPI(
    title="WhatsApp Price Intelligence API",
    description="Extract prices from WhatsApp & predict future prices",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(extraction_routes.router, prefix="/api", tags=["Extraction"])
app.include_router(prediction_routes.router, prefix="/api", tags=["Prediction"])
app.include_router(stats_routes.router, prefix="/api", tags=["Statistics"])
app.include_router(aliment_routes.router, prefix="/api", tags=["Aliments"])
app.include_router(aliment_prediction_routes.router, prefix="/api", tags=["Aliments-Prediction"])

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "WhatsApp Price Intelligence",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
