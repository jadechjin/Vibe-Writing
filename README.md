# 论文工作流系统

实验体系驱动、证据约束、G0–G5 门禁推进的论文工作流平台。

## 背景

传统论文写作工具偏向自由编辑或自由对话生成，但实验型论文的核心难点是如何把实验体系、图表、分析结果、证据链、提纲、草稿与审批过程稳定地串成可追溯闭环。

本项目解决的问题：

- 论文写作围绕**实验体系**推进，而不是围绕零散文档推进
- 图表、分析结果与正文之间形成**可验证的证据链**
- Figure Plan、Manifest、Evidence Matrix、Outline、Draft 等关键工件具备**版本化、可审批、可追溯**能力
- 长任务通过统一工作流与状态反馈机制执行，不同步阻塞或自由跳步

面向用户：以实验为中心推进毕业论文的学生、需要审查图表与草稿一致性的导师、希望搭建"受控生成 + 工作流门禁"系统的开发者。

## 功能特性

- **G0–G5 门禁推进**：每个阶段必须满足门禁条件才能推进，不允许自由跳步
- **Evidence Matrix 唯一事实源**：Draft 只能基于已批准 claims 生成
- **批量操作支持**：批量审批 claims、批量确认资产 QC
- **实时任务反馈**：WebSocket 驱动的长任务进度展示与 Toast 通知
- **异步生成**：Figure Plan、Manifest、Evidence Matrix、Outline、Draft 均异步返回任务句柄
- **多实验体系管理**：支持同一项目下多个实验体系并行推进

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- Docker / Docker Compose

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd <repo>

# 安装后端依赖
cd backend && python -m pip install -e ".[dev]" && cd ..

# 安装前端依赖
cd frontend && npm install && cd ..
```

### 运行

**1. 启动基础设施**

```bash
bash scripts/dev-up.sh
```

启动 PostgreSQL、Redis、MinIO、Temporal。停止：`bash scripts/dev-down.sh`

**2. 数据库迁移**

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

**3. 配置前端环境变量**

参考 `frontend/.env.example`：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/tasks
```

**4. 启动服务**

```bash
# 后端
uvicorn app.main:app --app-dir backend --reload

# 前端（新终端）
cd frontend && npm run dev
```

## 使用说明

### 工作流

单实验体系完整闭环：

```
项目创建 → 体系定义(G0) → Figure Plan(G1) → 数据上传/分析(G2)
→ Manifest/资产确认(G3) → Evidence Matrix + Outline(G4) → Draft 审批(G5)
```

门禁映射：

| Gate | 状态条件 |
|------|---------|
| G0 | `System_Defined` |
| G1 | `Figure_Plan_Ready` |
| G2 | `Data_Uploaded + Analysis_Ready` |
| G3 | `Assets_Confirmed` |
| G4 | `Evidence_Matrix_Ready + Outline_Ready` |
| G5 | `Chapter_Approved` |

### 示例

```bash
# 创建项目
POST /api/projects
{ "title": "我的论文项目" }

# 创建实验体系
POST /api/projects/{id}/systems
{ "name": "实验体系 A" }

# 推进门禁
POST /api/systems/{id}/advance

# 查询工作流状态
GET /api/systems/{id}/workflow
```

## 配置说明

### 前端环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `NEXT_PUBLIC_API_BASE_URL` | 后端 API 地址 | `http://localhost:8000/api` |
| `NEXT_PUBLIC_WS_URL` | WebSocket 地址 | `ws://localhost:8000/ws/tasks` |

### 后端环境变量（`THESIS_` 前缀）

| 变量 | 说明 |
|------|------|
| `THESIS_DATABASE_URL` | PostgreSQL 连接串 |
| `THESIS_REDIS_URL` | Redis 连接串 |
| `THESIS_TEMPORAL_HOST` | Temporal 地址 |
| `THESIS_MINIO_ENDPOINT` | MinIO 端点 |
| `THESIS_MINIO_ACCESS_KEY` | MinIO 访问密钥 |
| `THESIS_MINIO_SECRET_KEY` | MinIO 密钥 |
| `THESIS_MINIO_BUCKET` | 存储桶名称 |

开发环境内置本地默认值，生产环境必须覆盖。

### 基础设施默认端口

| 服务 | 端口 |
|------|------|
| PostgreSQL | 5432 |
| Redis | 6379 |
| MinIO API | 9000 |
| MinIO Console | 9001 |
| Temporal | 7233 |

## 项目结构

```
.
├── backend/                FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── modules/        业务模块（projects, systems, assets, evidence, drafts...）
│   │   ├── api/            路由聚合
│   │   ├── realtime/       WebSocket 广播
│   │   └── workflows/      Temporal workflow 定义
│   └── tests/              集成测试
├── frontend/               Next.js + React Query
│   ├── app/                页面路由
│   ├── components/
│   │   ├── gates/          G0–G5 工作台面板
│   │   ├── ui/             共享 UI 原语（ActionButton, SectionCard 等）
│   │   └── dashboard/      项目仪表盘组件
│   ├── hooks/              React Query hooks
│   └── styles/             共享样式常量
├── infra/                  Docker Compose 本地基础设施
├── scripts/                启停辅助脚本
└── llmdoc/                 项目架构文档
    ├── overview/           项目背景与仓库现状
    ├── architecture/       系统与模块设计
    ├── reference/          数据模型、API、事件契约
    └── guides/             开发与执行指南
```

## 开发指南

**文档优先**：开始任何实现前先阅读 `llmdoc/index.md`。

```bash
# 后端测试
python -m pytest backend/tests

# 后端 lint
python -m ruff check backend

# 前端类型检查
cd frontend && npm run typecheck

# 前端 smoke tests（G1–G5 面板级）
cd frontend && npm run test:smoke

# Alembic 迁移
python -m alembic -c backend/alembic.ini upgrade head
```

核心不变式：

- 所有生成类动作统一异步执行并返回句柄
- Draft 只能基于已批准 claims 生成
- WebSocket 是长任务反馈主通道
- 门禁推进必须满足 blocker 校验，不允许跳步

## FAQ

**这是通用 AI 论文生成器吗？**
不是。它是实验体系驱动、证据约束、门禁推进的工作流平台，生成内容必须基于已确认的实验证据。

**当前可以用于真实论文生产吗？**
G0–G5 全链已基本打通，核心 API 和工作台面板可用。Temporal 真实编排和部分生成器仍是占位实现，建议先在本地验证流程再用于生产。

**为什么强调 Evidence Matrix？**
项目将其定义为唯一事实源，草稿必须基于已确认 claims 与证据关系生成，不允许脱离实验事实自由扩写。

## Roadmap

近期：

- G4/G5 面板 smoke test 覆盖（EvidenceMatrixPanel + DraftPanel）
- G4 workbench 精化：claim 审批分组、binding 状态反馈
- G5 workbench 精化：draft 分组、折叠预览、决策标记

中期：

- 完善审批与退回机制
- Temporal 真实长流程编排落地
- 提升资产与分析结果的可追溯性
- 扩展多实验体系协同能力

## 贡献方式

1. 阅读 `llmdoc/index.md` 了解系统不变式
2. 明确目标与影响范围
3. 补充或更新测试
4. 提交前运行 `pytest` + `ruff` + `typecheck` + `test:smoke`
5. 保持代码、README 与 `llmdoc/` 一致

## License

当前仓库尚未提供明确的开源许可证文件。如计划对外开源，请在根目录补充 `LICENSE` 文件。
