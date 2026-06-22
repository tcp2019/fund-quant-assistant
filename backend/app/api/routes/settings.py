import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_db
from app.db.models import StrategyConfig
from app.schemas.settings import (
    DEFAULT_TEMPLATES,
    DEFAULT_THRESHOLDS,
    StrategyOut,
    StrategyUpdateIn,
)
from app.services.signals.engine import run_signal_engine

router = APIRouter(prefix="/api/settings", tags=["settings"])

VALID_TEMPLATES = {"conservative", "balanced", "aggressive", "custom"}


def _config_to_out(config: StrategyConfig) -> StrategyOut:
    target = json.loads(config.target_weights_json) or DEFAULT_TEMPLATES["balanced"]
    thresholds = json.loads(config.thresholds_json) or DEFAULT_THRESHOLDS
    fund_targets = json.loads(config.fund_target_weights_json or "{}")
    if not isinstance(fund_targets, dict):
        fund_targets = {}
    return StrategyOut(
        template_name=config.template_name,
        target_weights=target,
        thresholds=thresholds,
        intra_category_mode=config.intra_category_mode or "equal",
        fund_target_weights=fund_targets,
    )


def _get_or_seed_config(session: Session) -> StrategyConfig:
    config = session.exec(select(StrategyConfig)).first()
    if config is not None:
        return config

    config = StrategyConfig(
        template_name="balanced",
        target_weights_json=json.dumps(DEFAULT_TEMPLATES["balanced"]),
        thresholds_json=json.dumps(DEFAULT_THRESHOLDS),
        intra_category_mode="equal",
        fund_target_weights_json="{}",
    )
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def _resolve_target_weights(payload: StrategyUpdateIn) -> dict[str, float]:
    if payload.template_name == "custom":
        if not payload.target_weights:
            raise HTTPException(status_code=422, detail="custom template requires target_weights")
        total = sum(payload.target_weights.values())
        if not (0.99 <= total <= 1.01):
            raise HTTPException(
                status_code=422,
                detail=f"target_weights must sum to 1.0, got {total:.4f}",
            )
        return payload.target_weights

    template = DEFAULT_TEMPLATES.get(payload.template_name)
    if template is None:
        raise HTTPException(status_code=422, detail=f"unknown template: {payload.template_name}")
    return template


def _validate_fund_target_weights(weights: dict[str, float]) -> None:
    total = sum(weights.values())
    if not (0.99 <= total <= 1.01):
        raise HTTPException(
            status_code=422,
            detail=f"fund_target_weights must sum to 1.0, got {total:.4f}",
        )


@router.get("/strategy", response_model=StrategyOut)
def get_strategy(session: Session = Depends(get_db)):
    config = _get_or_seed_config(session)
    return _config_to_out(config)


@router.put("/strategy", response_model=StrategyOut)
def update_strategy(payload: StrategyUpdateIn, session: Session = Depends(get_db)):
    if payload.template_name not in VALID_TEMPLATES:
        raise HTTPException(status_code=422, detail=f"invalid template_name: {payload.template_name}")

    config = _get_or_seed_config(session)
    target_weights = _resolve_target_weights(payload)

    thresholds = {**DEFAULT_THRESHOLDS}
    if payload.thresholds is not None:
        thresholds.update(payload.thresholds.model_dump())

    config.template_name = payload.template_name
    config.target_weights_json = json.dumps(target_weights)
    config.thresholds_json = json.dumps(thresholds)

    mode = payload.intra_category_mode or config.intra_category_mode or "equal"
    if mode == "custom":
        if not payload.fund_target_weights:
            raise HTTPException(
                status_code=422,
                detail="custom intra_category_mode requires fund_target_weights",
            )
        _validate_fund_target_weights(payload.fund_target_weights)
        config.fund_target_weights_json = json.dumps(payload.fund_target_weights)
    elif payload.fund_target_weights is not None:
        _validate_fund_target_weights(payload.fund_target_weights)
        config.fund_target_weights_json = json.dumps(payload.fund_target_weights)
    config.intra_category_mode = mode

    session.add(config)
    session.commit()
    session.refresh(config)

    run_signal_engine(session)
    return _config_to_out(config)
