# v2.1 历史回测+组合优化器+多数据源 设计规格

> **Status:** active | **Created:** 2026-06-27

## 目标

验证信号有效性、科学配置权重、防止单点数据故障。

## A. 历史信号回测

- 对每个历史快照重新运行信号引擎，记录当时的买卖建议
- 对比"如果执行建议"vs"不执行"的后续收益差异
- 新增 API `POST /api/backtest/run` 返回回测结果
- 前端 BacktestPanel 展示简化版回测结果（信号数、命中率、超额收益）

## B. 组合优化器

- 基于当前持仓 + 策略目标权重，用简单的均值-方差优化给出建议配置
- 使用 scipy.optimize.minimize 最小化组合方差
- 约束：权重总和=1，各基金权重≥0，大类权重在目标±偏差范围内
- 新增 `services/optimizer.py` + API `POST /api/analysis/optimize`

## C. 多数据源

- 新增 tushare 作为备用 NAV 数据源
- `fetch_nav_fallback(code, primary='akshare', fallback='tushare')`
- akshare 失败时自动切换
- 环境变量 `TUSHARE_TOKEN` 配置

## 不包含

- 完整的事件驱动回测引擎
- Black-Litterman 模型
- 实时行情推送

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
