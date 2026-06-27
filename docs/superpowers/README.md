# Superpowers 文档目录

Spec 与 Plan 分目录管理，按生命周期归档。

## 目录结构

```
docs/superpowers/
├── README.md                 # 本说明 + 功能索引
├── specs/
│   ├── active/               # 当前有效的设计规格
│   └── archived/             # 已被新版本取代的 spec
├── plans/
│   ├── active/               # 进行中或待执行的实现计划
│   ├── completed/            # 已全部执行完毕
│   └── superseded/           # 执行中途被新 plan 取代
└── templates/
    ├── spec-template.md
    └── plan-template.md
```

## 规则速查

| 事件 | Spec | Plan |
|------|------|------|
| 新功能 | 在 `specs/active/` 新建 | 在 `plans/active/` 新建 |
| 功能迭代（v1 已交付） | 更新 active 内 spec，或新建后把旧的移到 `archived/` | **新建** plan，旧 plan 移到 `completed/` |
| Plan 执行完成 | 不变 | 移到 `plans/completed/` |
| Plan 执行中途大改 | 按需更新 spec | 旧 plan → `superseded/`，新建 plan 到 `active/` |
| Spec 被 v2 完全取代 | 旧 spec → `archived/`，顶部注明 `Superseded by:` | — |

**原则：** Spec 可演进；Plan 是一次执行快照——新需求新建 plan，不无限改旧 plan。

## 文件命名

- Spec: `YYYY-MM-DD-<topic>-design.md`
- Plan: `YYYY-MM-DD-<feature-name>.md`

## 功能索引

| 功能 | 当前 Spec | 当前 Plan | 历史 |
|------|-----------|-----------|------|
| 基金量化助手（Fund Quant Assistant） | [2026-06-21-fund-quant-assistant-design.md](specs/active/2026-06-21-fund-quant-assistant-design.md) | — | [v1](plans/completed/2026-06-21-fund-quant-assistant.md) · [v1.0.1](plans/completed/2026-06-21-alipay-ocr-formats.md) · [v1.1](plans/completed/2026-06-21-v11-dashboard-import-pipeline.md) |
| v1.2 候选/搜索/通知 | [2026-06-21-v12-recommendations-notifications-design.md](specs/active/2026-06-21-v12-recommendations-notifications-design.md) | — | [plan](plans/completed/2026-06-21-v12-recommendations-notifications.md) |
| v1.3 类内增配分配 | [2026-06-22-intra-category-rebalance-allocation-design.md](specs/active/2026-06-22-intra-category-rebalance-allocation-design.md) | — | [plan](plans/completed/2026-06-22-intra-category-rebalance-allocation.md) |
| v1.4 机会中心 + 热点雷达 | [2026-06-22-opportunities-hotspot-radar-design.md](specs/active/2026-06-22-opportunities-hotspot-radar-design.md) | — | [plan](plans/completed/2026-06-22-opportunities-hotspot-radar.md) |
| v1.5 组合管理基础 A/B/C/D | [2026-06-22-portfolio-management-foundation-design.md](specs/active/2026-06-22-portfolio-management-foundation-design.md) | — | [plan](plans/completed/2026-06-22-portfolio-management-foundation.md) |
| v1.6 信号一致性 · 结构优先 | [2026-06-22-signal-coherence-structural-first-design.md](specs/active/2026-06-22-signal-coherence-structural-first-design.md) | — | [plan](plans/completed/2026-06-22-signal-coherence-structural-first.md) |
| v1.7 数据质量与体验增强 | [2026-06-27-data-quality-and-ux-enhancement-design.md](specs/active/2026-06-27-data-quality-and-ux-enhancement-design.md) | [plan](plans/completed/2026-06-27-data-quality-and-ux-enhancement.md) | — |
| v1.8 NAV复权+业绩增强+定期报告 | [2026-06-27-nav-accuracy-signals-report-design.md](specs/active/2026-06-27-nav-accuracy-signals-report-design.md) | [plan](plans/completed/2026-06-27-nav-accuracy-signals-report.md) | — |
| v1.9 风格因子+宏观感知+模拟调仓 | [2026-06-27-factor-macro-whatif-design.md](specs/active/2026-06-27-factor-macro-whatif-design.md) | [plan](plans/completed/2026-06-27-factor-macro-whatif.md) | — |
| v2.0 动态权重+新手引导+PWA | [2026-06-27-adaptive-onboarding-pwa-design.md](specs/active/2026-06-27-adaptive-onboarding-pwa-design.md) | [plan](plans/active/2026-06-27-adaptive-onboarding-pwa.md) | — |
