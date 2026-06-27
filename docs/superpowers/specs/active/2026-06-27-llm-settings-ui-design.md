# v2.6.1 LLM 设置闭环 设计规格

> **Status:** active
> **Created:** 2026-06-28
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Parent spec:** [2026-06-27-retail-ux-convergence-design.md](./2026-06-27-retail-ux-convergence-design.md)

## 目标

在 v2.3 AI 解读与 v2.6 设置页基础上，让用户在**设置页**配置 LLM（API Key、接口地址、模型）并测试连接，无需编辑 `.env`。

## 范围

### 包含

1. **前端 localStorage** — 存 `api_key` / `base_url` / `model`（与浏览器通知偏好同模式，不上传服务端持久化）
2. **设置页区块** — 「AI 信号解读」：Key（密码框）、Base URL、Model、保存、测试连接
3. **解读请求** — `SignalsTable` 调用 interpret 时附带 localStorage 中的覆盖项
4. **后端测试端点** — `POST /api/settings/llm/test`，最小 chat 请求验证连通性
5. **interpret 扩展** — 请求体支持 `base_url`、`model` 覆盖（与已有 `api_key` 一致）

### 不包含

- 服务端持久化 LLM 配置（仍可用 `.env` 作服务端默认）
- 流式输出、批量解读
- 设置页展示已缓存的 interpretation

## 架构

```
SettingsPage → localStorage (llmSettings.ts)
SignalsTable → POST /api/signals/{id}/interpret { api_key?, base_url?, model? }
SettingsPage → POST /api/settings/llm/test { api_key?, base_url?, model? }
                      ↓
              llm_interpreter (override > settings.llm_*)
```

## 降级

| 场景 | 行为 |
|------|------|
| 无 Key（本地无、.env 无） | 测试返回 400；解读返回 null |
| 测试超时/401 | 返回 `ok: false` + 简短错误 |
| 仅有 .env Key | 不填本地 Key 时 interpret 仍可用服务端配置 |

## 验收标准

| # | 项 | 标准 |
|---|-----|------|
| 1 | 设置页 | 可保存 Key / URL / Model |
| 2 | 测试 | 成功显示「连接成功」；失败显示可读错误 |
| 3 | 解读 | 配置 Key 后 `/advice` AI 解读可用 |
| 4 | 回归 | 后端测试全绿；前端 build 通过 |

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-28 | tcp | 初始版本 |
