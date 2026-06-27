"""Tests for llm_interpreter service."""

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm_interpreter import _build_messages, _build_user_message, interpret_signal


def test_build_user_message_reduce_signal():
    signal = {
        "signal_type": "reduce",
        "fund_code": "110011",
        "fund_name": "易方达优质精选混合",
        "score": -0.82,
        "strength": 4,
        "suggested_amount": -30000,
        "reasons": [
            {
                "layer": "concentration",
                "rule": "high_correlation",
                "detail": "与华夏债券A相关系数0.89",
                "paired_fund_name": "华夏债券A",
                "correlation": 0.89,
            },
        ],
    }
    msg = _build_user_message(signal, total_value=500000, weight_pct=38)
    assert "减仓" in msg
    assert "易方达优质精选混合" in msg
    assert "110011" in msg
    assert "-0.8" in msg
    assert "38%" in msg
    assert "高相关" in msg
    assert "相关系数0.89" in msg


def test_build_user_message_add_category():
    signal = {
        "signal_type": "add",
        "fund_code": "",
        "category_label": "股票型",
        "score": 35.0,
        "strength": 3,
        "suggested_amount": 20000,
        "reasons": [
            {
                "layer": "rebalance",
                "rule": "category_underweight",
                "detail": "股票型低配5.2%，建议增配¥20,000",
            }
        ],
    }
    msg = _build_user_message(signal, total_value=500000, weight_pct=0)
    assert "增配" in msg
    assert "股票型" in msg
    assert "大类低配" in msg
    assert "50.0万" in msg


def test_build_messages_structure():
    signal = {"signal_type": "hold", "reasons": []}
    messages = _build_messages(signal)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "个人投资者" in messages[0]["content"]


def _fake_response(content: str):
    """Build a fake httpx Response that survives raise_for_status()."""
    import httpx as _httpx

    request = _httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return _httpx.Response(200, json={"choices": [{"message": {"content": content}}]}, request=request)


@pytest.mark.asyncio
async def test_interpret_signal_no_api_key(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", None)
    result = await interpret_signal({"signal_type": "hold", "reasons": []})
    assert result is None


@pytest.mark.asyncio
async def test_interpret_signal_mock_success(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", "sk-test")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_fake_response("建议继续持有，各维度表现正常。"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await interpret_signal({"signal_type": "hold", "reasons": []})

    assert result == "建议继续持有，各维度表现正常。"


@pytest.mark.asyncio
async def test_interpret_signal_mock_http_error(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", "sk-test")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        return_value=httpx.Response(401, json={"error": "unauthorized"},
                                    request=httpx.Request("POST", "https://test/")))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await interpret_signal({"signal_type": "hold", "reasons": []})

    assert result is None


@pytest.mark.asyncio
async def test_interpret_signal_mock_timeout(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", "sk-test")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await interpret_signal({"signal_type": "hold", "reasons": []})

    assert result is None


@pytest.mark.asyncio
async def test_interpret_signal_api_key_override(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", "sk-server")

    last_key: str | None = None

    async def capture_post(url, *, headers, json, **kwargs):
        nonlocal last_key
        last_key = headers.get("Authorization", "")
        return _fake_response("ok")

    mock_client = AsyncMock()
    mock_client.post = capture_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await interpret_signal(
            {"signal_type": "hold", "reasons": []},
            api_key_override="sk-override",
        )

    assert result == "ok"
    assert last_key == "Bearer sk-override"
