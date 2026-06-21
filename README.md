# 基金量化助手（Fund Quant Assistant）

个人基金持仓管理与量化分析 Web 工具。通过上传持仓截图（支付宝、天天基金、腾讯理财通）导入基金，基于公开数据计算量化指标，并以可解释的规则引擎输出买入 / 卖出 / 观察建议。

> **免责声明：** 本产品仅供个人学习与持仓管理，**不构成任何投资建议**。所有信号与建议均为基于历史数据的规则化输出，不保证未来收益，使用前请自行判断风险。

## 功能

- **截图 OCR 导入** — 支持支付宝、天天基金、理财通持仓截图，人工确认后写入持仓
- **持仓概览 Dashboard** — 总市值、盈亏、权重、大类结构、集中度
- **基金数据同步** — 通过 akshare 拉取净值、基准、同类排名等公开数据
- **三层量化信号引擎** — 配置再平衡 + 风险集中度 + 业绩质量 → 综合评分与操作建议
- **策略参数配置** — 保守 / 平衡 / 激进模板，规则阈值可调
- **快照历史** — OCR 确认或手动编辑产生快照，支持历史对比
- **相关性 & 风险分析** — 相关系数矩阵、组合波动率、夏普、最大回撤
- **本地单用户部署** — SQLite 存储，数据留在本机

## 环境要求

- Python 3.11+
- Node.js 18+（推荐 20+）
- npm

可选：安装 `[ocr]` 依赖以启用 PaddleOCR 本地识图（未安装时 OCR 相关功能可能受限）。

## 安装

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 可选：本地 OCR
pip install -e ".[dev,ocr]"
```

首次启动会在 `backend/` 目录下创建 SQLite 数据库 `fund_quant.db`。

### 前端

```bash
cd frontend
npm install
```

## 启动开发环境

在项目根目录一键启动后端与前端：

```bash
chmod +x scripts/dev.sh   # 首次需要
./scripts/dev.sh
```

或分别启动：

```bash
# 终端 1 — 后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2 — 前端
cd frontend
npm run dev
```

访问地址：

| 服务 | URL |
|------|-----|
| 前端 | http://localhost:5173 |
| 后端 API | http://127.0.0.1:8000 |
| API 文档 | http://127.0.0.1:8000/docs |

前端通过 Vite 代理将 `/api` 请求转发至后端。

## 页面

| 路由 | 说明 |
|------|------|
| `/` | 总览 Dashboard |
| `/import` | 截图上传与 OCR 确认 |
| `/holdings` | 持仓明细与编辑 |
| `/signals` | 买卖信号（按优先级排序） |
| `/analysis` | 相关性、风险指标 |
| `/settings` | 目标配置、阈值、数据同步 |

## 测试

```bash
cd backend
source .venv/bin/activate
pytest tests -v
```

## 技术栈

- **前端：** React, TypeScript, Vite, Tailwind CSS, Recharts
- **后端：** Python, FastAPI, SQLModel, SQLite
- **数据：** akshare
- **OCR：** PaddleOCR（可选）

## 许可证

个人自用项目。公开数据来源于第三方接口，请遵守相应使用条款。
