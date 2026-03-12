from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_artifacts import router as artifacts_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_health import router as health_router
from app.api.routes_runs import router as runs_router
from app.api.routes_tasks import router as task_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db
from app.services.scheduler_service import (
    init_scheduler,
    shutdown_scheduler,
    start_scheduler,
    sync_enabled_tasks,
)

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    init_db()
    init_scheduler()
    start_scheduler()
    sync_enabled_tasks()

    yield

    shutdown_scheduler()
    logger.info("Application shutdown complete")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(task_router)
app.include_router(runs_router)
app.include_router(artifacts_router)
app.include_router(dashboard_router)
