# v2.3 AI 信号解读 Implementation Plan

> **Status:** completed
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-ai-signal-interpretation-design.md

**Goal:** 在信号引擎量化输出之上增加 LLM 驱动的自然语言解读，帮助零售投资者理解信号含义。

**Architecture:** 后端新增 llm_interpreter 服务 + interpret API 端点 + SignalRecord.interpretation 缓存列；前端 AJIInterpretation 懒加载组件。

**Tech Stack:** Python 3.13+ / FastAPI / httpx / OpenAI-compatible API, TypeScript / React 19 / Tailwind CSS

---

### Task 1: Config

**Files:** `backend/app/config.py`, `backend/.env.example`

- [x] 新增 `llm_api_key`, `llm_base_url`, `llm_model` 配置项

### Task 2: Database

**Files:** `backend/app/db/models.py`, `backend/app/db/session.py`

- [x] SignalRecord 新增 `interpretation TEXT` 列
- [x] Migration: `_ensure_signal_record_columns()` PRAGMA check

### Task 3: Schema

**Files:** `backend/app/schemas/signals.py`

- [x] SignalOut 新增 `interpretation: str | None`
- [x] 新增 `InterpretRequest`, `InterpretOut`

### Task 4: LLM Interpreter Service

**Files:** `backend/app/services/llm_interpreter.py`

- [x] `interpret_signal()` — 异步调用 OpenAI-compatible API
- [x] `_build_messages()` — 构造 system + user prompt
- [x] `_build_user_message()` — 结构化信号数据转中文 prompt
- [x] 降级：无 key / 异常 → None

### Task 5: API Endpoint

**Files:** `backend/app/api/routes/signals.py`

- [x] `POST /api/signals/{signal_id}/interpret` — 按需生成+缓存
- [x] `GET /api/signals` — SignalOut 填充 interpretation 字段

### Task 6: Frontend

**Files:** `frontend/src/types/index.ts`, `frontend/src/api/client.ts`, `frontend/src/components/SignalsTable.tsx`

- [x] Signal 类型新增 `interpretation`
- [x] `fetchSignalInterpretation()` API 函数
- [x] `AIInterpretation` 组件 — idle/loading/result/error 四态
- [x] 集成到 SignalDetailPanel

### Task 7: Tests

**Files:** `backend/tests/test_llm_interpreter.py`, `backend/tests/test_signals_engine.py`

- [x] Prompt 构建测试（减仓、增配、结构）
- [x] 无 API key 返回 None
- [x] Mock 成功/HTTP 错误/超时
- [x] API key override 验证
- [x] Interpret endpoint 缓存返回
- [x] Interpret endpoint 404
- [x] list_signals 包含 interpretation
