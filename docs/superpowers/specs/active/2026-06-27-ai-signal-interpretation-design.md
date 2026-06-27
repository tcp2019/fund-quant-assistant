# v2.3 AI 信号解读 设计规格

> **Status:** active
> **Created:** 2026-06-27

## 目标

在信号引擎的量化输出之上增加一层自然语言解读，帮助零售投资者理解"这个信号对我意味着什么？我应该怎么做？"

## 核心原则

LLM 只做翻译+润色，不做独立投资判断。信号引擎的输出是权威来源。

## 范围

### 包含

1. **LLM 解释器服务** — 结构化信号 → 中文自然语言解读（2-3 句话）
2. **API 端点** — `POST /api/signals/{id}/interpret` 按需生成 + 缓存
3. **数据库缓存** — SignalRecord 新增 `interpretation` 列
4. **前端 UI** — AI 解读按钮 + 懒加载 + 结果展示
5. **多 LLM 兼容** — 支持任何 OpenAI-compatible API

### 不包含

- 流式输出
- 批量生成所有信号解读
- 前端配置 LLM key 的 UI
- LLM 改写信号结论
- 市场行情数据注入 prompt

## 架构

```
用户点击「AI 解读」
  → POST /api/signals/{id}/interpret
    → 查 SignalRecord.interpretation（缓存命中 → 直接返回）
    → 构建 SignalOut + 组合 context
    → llm_interpreter.interpret_signal()
      → _build_messages() 构造 structured prompt
      → httpx → OpenAI-compatible API
      → 2-3 句中文解读
    → 写回 DB → 返回
  → 前端展示
```

## 数据流

### Prompt 结构

System: "你是面向个人投资者的基金组合助手..."
User (结构化):
```
信号类型：减仓
基金名称：易方达优质精选混合（110011）
综合评分：-0.82 / 强度：4/5
建议减仓：¥30,000
当前权重：38% / 组合总市值：¥500,000

触发原因：
- [再平衡] 大类超配：...
- [集中度] 高相关：与 XX 相关系数 0.89
- [业绩] 超额收益：近1年跑输同类4.2%
```

### API

`POST /api/signals/{signal_id}/interpret`
- Request: `{ api_key?: string }` — 可选请求级 key 覆盖
- Response: `{ signal_id, interpretation, cached }`

### 降级

| 场景 | 行为 |
|------|------|
| 无 LLM_API_KEY | 返回 `interpretation: null` |
| API 超时/401/500 | 返回 `null`，记录 warning |
| LLM 返回空 | 返回 `null` |

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 触发方式 | 懒加载（按需） | 避免批量生成延迟 |
| 缓存策略 | 写入 DB，一次生成永久复用 | 信号不变则解读不变 |
| 存储位置 | SignalRecord 新增列 | SQLite 单表最简单 |
| API 协议 | OpenAI-compatible | 兼容性最广 |
| 默认模型 | gpt-4o-mini | 轻量、中文能力强、成本低 |

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
