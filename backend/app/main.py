import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.backtest import router as backtest_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.opportunities import router as opportunities_router
from app.api.routes.settings import router as settings_router
from app.api.routes.data import router as data_router
from app.api.routes.funds import router as funds_router
from app.api.routes.ocr import router as ocr_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.signals import router as signals_router
from app.config import settings
from app.db.session import create_db_and_tables
from app.services.scheduler import run_scheduled_sync

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    scheduler: BackgroundScheduler | None = None
    if settings.auto_sync_enabled:
        scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        scheduler.add_job(
            run_scheduled_sync,
            "cron",
            hour=settings.auto_sync_hour,
            minute=settings.auto_sync_minute,
            id="daily_portfolio_sync",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "Auto sync scheduled daily at %02d:%02d Asia/Shanghai",
            settings.auto_sync_hour,
            settings.auto_sync_minute,
        )
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Fund Quant Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_router)
app.include_router(funds_router)
app.include_router(ocr_router)
app.include_router(data_router)
app.include_router(signals_router)
app.include_router(analysis_router)
app.include_router(settings_router)
app.include_router(opportunities_router)
app.include_router(backtest_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
