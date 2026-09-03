from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.database import Base, engine
from app.models import (
    AgentDecision,
    AuditEvent,
    Customer,
    PaymentAttempt,
    RecoveryAction,
    RecoveryCase,
    Transaction,
)

from app.routes.recovery import router as recovery_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="RecoverAI",
    description="AI-powered revenue recovery platform",
    version="0.1.0",
)

# ---------------------------------------------------------
# CORS — allow the frontend to call the API
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recovery_router)


@app.get("/")
async def root():
    return {
        "name": "RecoverAI",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }


@app.get("/health/database")
async def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception as error:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(error),
            },
        )