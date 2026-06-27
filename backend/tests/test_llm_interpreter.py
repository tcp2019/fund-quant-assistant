"""Tests for llm_interpreter service."""

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm_interpreter import _build_messages, _build_user_message, interpret_signal, test_llm_connection


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


def test_completions_url_deepseek_strips_v1_suffix():
    from app.services.llm_interpreter import _completions_url

    assert _completions_url("https://api.deepseek.com/v1") == "https://api.deepseek.com/chat/completions"
    assert _completions_url("https://api.openai.com/v1") == "https://api.openai.com/v1/chat/completions"


def test_extract_message_content_reasoning_fallback():
    from app.services.llm_interpreter import _extract_message_content

    choice = {"message": {"content": "", "reasoning_content": "思考过程"}}
    assert _extract_message_content(choice) == "思考过程"


def test_chat_payload_thinking_only_for_deepseek():
    from app.services.llm_interpreter import _chat_payload

    openai = _chat_payload("https://api.openai.com/v1", model="gpt-4o", messages=[], max_tokens=16)
    assert "thinking" not in openai

    deepseek = _chat_payload(
        "https://api.deepseek.com", model="deepseek-v4-flash", messages=[], max_tokens=16
    )
    assert deepseek["thinking"] == {"type": "disabled"}


def test_llm_base_url_blocks_loopback():
    from app.services.llm_interpreter import _llm_base_url_error

    assert _llm_base_url_error("http://127.0.0.1/v1") == "接口地址不可用"
    assert _llm_base_url_error("https://api.openai.com/v1") is None


@pytest.mark.asyncio
async def test_test_llm_connection_blocks_private_host(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", "sk-test")
    ok, error = await test_llm_connection(base_url_override="http://127.0.0.1/v1")
    assert ok is False
    assert error == "接口地址不可用"


@pytest.mark.asyncio
async def test_test_llm_connection_no_api_key(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", None)
    ok, error = await test_llm_connection()
    assert ok is False
    assert error == "未配置 API Key"


@pytest.mark.asyncio
async def test_test_llm_connection_success(monkeypatch):
    monkeypatch.setattr("app.services.llm_interpreter.settings.llm_api_key", "sk-test")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_fake_response("连接成功"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        ok, error = await test_llm_connection()

    assert ok is True
    assert error is None
