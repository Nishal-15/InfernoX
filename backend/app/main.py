from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.api.v1.router import api_router
from app.core.config import settings
from app.services.firms.ingestion import FirmsIngestionService
from app.db.database import SessionLocal, engine, Base
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Background scheduler
scheduler = AsyncIOScheduler()

async def scheduled_ingestion():
    logger.info("Running autonomous geospatial intelligence pipeline cycle...")
    try:
        db = SessionLocal()
        try:
            from app.services.autonomous.pipeline_runner import PipelineRunner
            result = await PipelineRunner.run_autonomous_cycle(db, use_demo=settings.DEMO_MODE)
            logger.info(f"Autonomous cycle result: {result}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error during scheduled autonomous cycle: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database tables...")
    try:
        import app.models
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        db = SessionLocal()
        try:
            from app.services.alert.engine import AlertEngine
            from app.models.pipeline import PipelineJob
            from datetime import datetime, timezone
            AlertEngine.seed_default_rules(db)
            try:
                from app.services.osm.ingestion import OsmIngestionService
                OsmIngestionService.seed_default_facilities(db)
            except Exception as fe:
                logger.warning(f"Could not seed industrial facilities: {fe}")
            try:
                from app.services.auth.seed import seed_saas_defaults
                seed_saas_defaults(db)
            except Exception as se:
                logger.warning(f"Could not seed SaaS defaults: {se}")

            # Restart recovery: Mark unfinished running jobs as INTERRUPTED
            interrupted = db.query(PipelineJob).filter(PipelineJob.status.in_(["RUNNING", "QUEUED"])).all()
            for j in interrupted:
                j.status = "INTERRUPTED"
                j.error_message = "Server restarted while job was in progress; state recovered on startup."
                j.completed_at = datetime.now(timezone.utc)
            if interrupted:
                db.commit()
                logger.info(f"Restart recovery: {len(interrupted)} interrupted jobs safely marked.")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not connect to database at startup: {e}. Tables will need to be initialized once DB is reachable.")

    logger.info("Starting background scheduler...")
    try:
        scheduler.add_job(
            scheduled_ingestion, 
            'interval', 
            minutes=settings.FIRMS_INGEST_INTERVAL_MINUTES,
            id='firms_ingestion_job',
            replace_existing=True
        )
        scheduler.start()
    except Exception as e:
        logger.warning(f"Could not start background scheduler: {e}")

    yield
    # Shutdown
    logger.info("Shutting down background scheduler...")
    if scheduler.running:
        scheduler.shutdown()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="InfernoX: AI-Based Industrial Fire & Persistent Thermal Source Intelligence Platform",
    lifespan=lifespan
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Thermal Intelligence API is running"}
