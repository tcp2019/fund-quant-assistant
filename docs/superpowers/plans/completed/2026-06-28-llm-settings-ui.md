# v2.6.1 LLM 设置闭环 Implementation Plan

> **Status:** completed
> **Created:** 2026-06-28
> **Spec:** [2026-06-27-llm-settings-ui-design.md](../../specs/active/2026-06-27-llm-settings-ui-design.md)
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** v2.3 AI interpret + v2.6 Settings 分区

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

## File Structure

| File | Responsibility |
|------|----------------|
| `frontend/src/utils/llmSettings.ts` | localStorage 读写与默认值 |
| `backend/app/services/llm_interpreter.py` | `test_llm_connection` + base_url/model override |
| `backend/app/schemas/settings.py` | `LlmTestIn` / `LlmTestOut` |
| `backend/app/schemas/signals.py` | `InterpretRequest` 扩展 |
| `backend/app/api/routes/settings.py` | `POST /llm/test` |
| `frontend/src/api/client.ts` | `testLlmConnection` |
| `frontend/src/pages/SettingsPage.tsx` | AI 解读设置 UI |
| `frontend/src/components/SignalsTable.tsx` | 解读时附带 LLM 覆盖 |

## Tasks

- [x] 1. Backend: extend interpreter + test endpoint + tests
- [x] 2. Frontend: llmSettings util + client + Settings UI + SignalsTable
- [x] 3. Docs: README index + move plan to completed
