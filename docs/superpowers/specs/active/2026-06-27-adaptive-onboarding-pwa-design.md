# v2.0 动态权重+新手引导+PWA 设计规格

> **Status:** active
> **Created:** 2026-06-27
> **Supersedes:** (none)
> **Superseded by:** (none)

## 目标

信号权重随市场波动自适应、新用户引导流程、PWA 移动端可用。

## A. 动态权重

在 `engine.py` 中根据宏观环境动态调整 `LAYER_WEIGHTS`：
- 环境tight → 风险层权重从0.3提到0.4，业绩层从0.3降到0.2
- 环境loose → 再平衡层从0.4提到0.5，业绩层保持
- neutral → 默认权重不变

新增 `services/signals/adaptive_weights.py`，`def get_adaptive_weights(environment: str) -> dict`

## B. 新手引导

Dashboard 首次加载（无持仓数据）时显示 step-by-step 引导：
1. 导入持仓（链接到 /import）
2. 同步数据
3. 查看信号

纯前端组件 `OnboardingGuide.tsx`，localStorage 记录是否已完成。

## C. PWA

添加 `vite-plugin-pwa`，manifest.json + service worker：
- 桌面快捷方式图标
- 离线缓存静态资源
- 安装提示

## 不包含

- 动态权重回测验证
- 多步骤引导动画
- 推送通知（已由现有通知系统覆盖）

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
