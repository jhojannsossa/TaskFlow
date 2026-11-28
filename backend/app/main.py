import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings
from backend.app.database.connection import get_db
from backend.app.services.birthday_runner import (
    run_birthday_notifications,
)

from backend.app.routers.auth import router as auth_router
from backend.app.routers.tasks import router as tasks_router
from backend.app.routers.lists import router as lists_router
from backend.app.routers.notifications import router as notifications_router
from backend.app.routers.dashboard import router as dashboard_router
from backend.app.routers.users import router as users_router


logger = logging.getLogger(__name__)


async def birthday_scheduler():
    """
    Comprueba los cumpleaños al iniciar
    y cada 24 horas mientras FastAPI esté activo.
    """
    while True:
        try:
            await asyncio.to_thread(
                run_birthday_notifications
            )
        except Exception:
            logger.exception(
                "Error al procesar cumpleaños."
            )

        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    birthday_task = asyncio.create_task(
        birthday_scheduler()
    )

    try:
        yield
    finally:
        birthday_task.cancel()

        try:
            await birthday_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API REST para la gestión de tareas "
        "personales y colaborativas."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

settings.AVATAR_UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/uploads/avatars",
    StaticFiles(
        directory=settings.AVATAR_UPLOAD_DIR
    ),
    name="avatars",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET", "POST", "PUT",
        "PATCH", "DELETE", "OPTIONS"
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(lists_router)
app.include_router(notifications_router)
app.include_router(dashboard_router)
app.include_router(users_router)


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
def database_health(
    db: Session = Depends(get_db),
):
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
