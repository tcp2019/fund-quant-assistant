import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.db.session import engine
from app.services.data_sync import sync_portfolio_funds
from app.services.holdings_revalue import revalue_holdings
from app.services.signals.engine import run_signal_engine

logger = logging.getLogger(__name__)
SHANGHAI = ZoneInfo("Asia/Shanghai")


def run_scheduled_sync() -> None:
    started = datetime.now(SHANGHAI)
    logger.info("Scheduled portfolio sync started at %s", started.isoformat())
    try:
        with Session(engine) as session:
            result = sync_portfolio_funds(session)
            revalue = revalue_holdings(session)
            signals = run_signal_engine(session)
            logger.info(
                "Scheduled sync finished: synced=%s revalued=%s signals=%s as_of=%s",
                result.get("synced"),
                revalue.get("updated"),
                len(signals),
                revalue.get("as_of_date"),
            )
    except Exception:
        logger.exception("Scheduled portfolio sync failed")
