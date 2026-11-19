from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings
from backend.app.database.connection import get_db


app = FastAPI(
    title=settings.APP_NAME,
    description="API REST para la gestión de tareas personales y colaborativas.",
    version=settings.APP_VERSION,
)


@app.get("/")
def root():
    return {
        "application": "TaskFlow",
        "message": "Bienvenido a TaskFlow API",
        "version": settings.APP_VERSION,
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
    }


@app.get("/api/health/database")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": settings.DB_NAME,
            "connection": "successful",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )

