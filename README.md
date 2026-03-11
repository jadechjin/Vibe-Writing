# 论文工作流系统

一个以实验体系为最小业务单元、以 Evidence Matrix 为唯一事实源、以 G0–G5 门禁推进的论文工作流平台。

> 当前状态：**MVP 初始化阶段**。仓库已经具备前后端骨架、数据模型、迁移与测试基线，但尚未完成端到端业务闭环，现阶段更适合做架构验证、开发接入与后续迭代。

## 项目背景 / 目标

传统论文写作工具通常偏向自由编辑或自由对话生成，但实验型论文的关键难点并不只是“写正文”，而是如何把实验体系、图表、分析结果、证据链、提纲、草稿与审批过程稳定地串成一个可追溯闭环。

这个项目希望解决的问题包括：

- 让论文写作围绕**实验体系**推进，而不是围绕零散文档推进
- 让图表、分析结果与正文之间形成**可验证的证据链**
- 让 Figure Plan、Manifest、Evidence Matrix、Outline、Draft 等关键工件具备**版本化、可审批、可退回、可追溯**能力
- 让长任务通过统一的工作流与状态反馈机制执行，而不是同步阻塞或自由跳步

面向用户包括：

- 以实验为中心推进毕业论文的学生
- 需要审查图表、证据与草稿一致性的导师或协作者
- 希望搭建“受控生成 + 工作流门禁”系统的开发者

## 当前状态

当前仓库处于 **MVP 初始化阶段**，已经落地的内容主要是基础骨架和契约基线，而不是完整业务系统。

### 已落地基础

- **前后端骨架**
  - `backend/` 已提供 FastAPI 应用入口、统一异常响应基础设施与 WebSocket 样例通道
  - `frontend/` 已提供 Next.js 页面骨架与基础布局壳层
- **数据层基线**
  - 已建立项目、实验体系、资产、Manifest、Evidence、Draft、Workflow 相关 ORM 模型与 Alembic 迁移
  - 已补齐关键数据约束测试，包括 `claim_evidence_links` 的部分唯一索引与 `AnalysisRun` 删除限制语义
- **开发基础设施**
  - 本地 PostgreSQL、Redis、MinIO、Temporal 的 Docker Compose 编排
  - 后端 pytest、Ruff、Alembic 基线可运行
- **文档系统**
  - 已建立 `llmdoc/`，用于维护项目背景、架构、数据模型、API 契约与开发指南

### 已定义但未完整实现

以下内容目前主要以**文档契约、骨架接口或占位实现**形式存在，还不是完整可用功能：

- 项目 / 体系 / 资产 / Evidence / Draft 的完整业务 API
- G0–G5 门禁驱动的状态推进逻辑
- 基于 Temporal 的真实长流程编排
- 真实任务广播与前端任务托盘集成
- 完整的 Figure Plan → Evidence Matrix → Outline → Draft 端到端闭环

### 当前不应误解为“已完成”的部分

为了避免误读，需要特别说明：

- `backend/app/api/router.py` 当前仍是空路由壳子
- `backend/app/workflows/system_workflow.py` 当前是占位 workflow
- `backend/app/realtime/broadcaster.py` 当前是 no-op broadcaster
- `frontend/app/projects/**` 当前仍以 placeholder 页面为主

也就是说，仓库当前重点是**把系统边界、模型、约束、文档和启动基线先搭起来**，而不是已经交付完整产品。

## 核心特点

即使还处于 MVP 初始化阶段，项目方向已经比较明确：

- **实验体系优先**：实验体系是最小推进单元
- **Evidence Matrix 优先**：Evidence Matrix 是唯一事实源
- **门禁驱动而非自由跳步**：G0–G5 门禁控制流程推进
- **生成动作异步化**：长任务统一返回 `workflow_id` / `job_id`
- **证据绑定具备强约束**：`claim_evidence_links.analysis_run_id` 可为空，但一旦引用某个 `AnalysisRun`，数据库必须拒绝删除该被引用记录

## MVP 工作流目标

单实验体系闭环目标如下：

`项目创建 → 体系定义 → Figure Plan → 数据上传/分析 → Manifest → Evidence Matrix → Outline → Section Draft → Review / Approve`

固定门禁映射：

- G0 → `System_Defined`
- G1 → `Figure_Plan_Ready`
- G2 → `Data_Uploaded + Analysis_Ready`
- G3 → `Assets_Confirmed`
- G4 → `Evidence_Matrix_Ready + Outline_Ready`
- G5 → `Chapter_Approved`

## 技术栈

### 前端

- Next.js 16
- React 19
- React Query
- TypeScript

### 后端

- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Redis
- Temporal
- MinIO / S3 兼容对象存储

### 执行层

- Claude Code
- Vision executor
- Python analysis worker

## 快速开始

> 目标：**启动当前骨架、验证本地基线**，而不是跑通完整论文业务流程。

### 环境要求

建议准备：

- Python 3.11+
- Node.js 20+
- npm
- Docker / Docker Compose
- Bash 兼容 shell（`scripts/*.sh` 需要）

### 1. 启动基础设施

```bash
bash scripts/dev-up.sh
```

停止：

```bash
bash scripts/dev-down.sh
```

默认会启动：

- PostgreSQL
- Redis
- MinIO
- Temporal

### 2. 安装后端依赖

```bash
cd backend
python -m pip install -e ".[dev]"
cd ..
```

### 3. 运行数据库迁移

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

### 4. 启动后端

```bash
uvicorn app.main:app --app-dir backend --reload
```

预期结果：

- FastAPI 应用可以在本地启动
- API 前缀默认为 `/api`
- WebSocket 样例端点 `/ws/tasks` 可建立连接并收到 bootstrap / heartbeat 消息

### 5. 配置并启动前端

参考 `frontend/.env.example`：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/tasks
```

启动前端：

```bash
cd frontend
npm install
npm run dev
cd ..
```

预期结果：

- Next.js 本地页面可访问
- 当前页面主要用于验证布局壳层与占位路由，不代表完整业务流程已可操作

### 6. 运行验证命令

后端测试：

```bash
python -m pytest backend/tests
```

后端静态检查：

```bash
python -m ruff check backend
```

前端类型检查：

```bash
cd frontend && npm run typecheck && cd ..
```

## 使用说明

### 当前可实际使用的内容

当前仓库更适合用于以下场景：

- 阅读架构与数据建模文档
- 启动本地基础设施
- 运行 Alembic 迁移
- 启动 FastAPI / Next.js 骨架
- 连接 WebSocket 样例通道验证事件格式
- 运行测试与静态检查，作为后续开发基线

### 当前建议的使用顺序

1. 阅读 `llmdoc/index.md`
2. 阅读 `llmdoc/overview/*`
3. 阅读与当前任务相关的 `llmdoc/architecture/*` 和 `llmdoc/reference/*`
4. 启动基础设施并执行迁移
5. 启动前后端骨架
6. 运行测试与 lint，确认基线正常

### 目前还不能直接期待的能力

在当前仓库版本中，以下内容仍属于目标能力，而不是现成可用功能：

- 完整的项目/体系/资产 CRUD API
- 完整的门禁推进 API（如 `/systems/{id}/advance` 的真实 blocker 判定）
- 完整的 Figure Plan / Evidence Matrix / Outline / Draft 生成流程
- 完整的任务广播、审批与多页面业务交互

## 配置说明

### 前端环境变量

参考 `frontend/.env.example`：

- `NEXT_PUBLIC_API_BASE_URL`
  - 前端访问后端 API 的基础地址
  - 示例：`http://localhost:8000/api`
- `NEXT_PUBLIC_WS_URL`
  - 前端连接任务状态 WebSocket 的地址
  - 示例：`ws://localhost:8000/ws/tasks`

### 后端配置

后端使用 `THESIS_` 前缀环境变量，例如：

- `THESIS_APP_ENV`
- `THESIS_DATABASE_URL`
- `THESIS_REDIS_URL`
- `THESIS_TEMPORAL_HOST`
- `THESIS_MINIO_ENDPOINT`
- `THESIS_MINIO_ACCESS_KEY`
- `THESIS_MINIO_SECRET_KEY`
- `THESIS_MINIO_BUCKET`

开发环境下内置了本地默认值；非开发环境必须覆盖默认数据库与 MinIO 凭据。

### 基础设施默认端口

来自 `infra/docker-compose.yml`：

- PostgreSQL: `5432`
- Redis: `6379`
- MinIO API: `9000`
- MinIO Console: `9001`
- Temporal: `7233`

## 项目结构

```text
.
├─ llmdoc/                  项目文档系统
│  ├─ overview/             项目背景与仓库现状
│  ├─ architecture/         系统与模块设计
│  ├─ reference/            数据模型、API、事件契约
│  └─ guides/               开发与执行指南
├─ backend/                 FastAPI + SQLAlchemy + Alembic
│  ├─ app/
│  │  ├─ api/
│  │  ├─ common/
│  │  ├─ core/
│  │  ├─ executors/
│  │  ├─ persistence/
│  │  ├─ realtime/
│  │  └─ workflows/
│  ├─ alembic/
│  └─ tests/
├─ frontend/                Next.js 页面骨架与工作台壳层
├─ infra/                   本地基础设施编排
├─ scripts/                 启停辅助脚本
└─ 论文写作系统_前后端改造方案_最终版_补充技术栈说明.md
```

## API / 接口说明

### 当前已存在的接口基础

- FastAPI 应用入口与统一异常响应
- `/ws/tasks` WebSocket 样例通道
- 统一响应模型 `ApiResponse<T>`

统一响应格式：

```ts
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total?: number
    page?: number
    limit?: number
  }
}
```

### 规划中的 API 契约

以下内容来自 `llmdoc/reference/api-contracts.md`，代表 **MVP 目标接口契约**，当前尚未全部落地为真实路由：

#### 项目与实验体系

- `POST /projects`
- `GET /projects/{id}`
- `POST /projects/{id}/systems`
- `PATCH /systems/{id}`
- `GET /projects/{id}/dashboard`

#### 资产

- `POST /assets/upload`
- `GET /assets/{id}`
- `POST /assets/{id}/bind`

#### 图表与证据

- `POST /systems/{id}/figure-plans/generate`
- `PATCH /figure-plans/{id}`
- `POST /systems/{id}/evidence-matrix/generate`
- `PATCH /claims/{id}`

#### 写作与审批

- `POST /systems/{id}/outline/generate`
- `POST /systems/{id}/sections/{sectionKey}/draft`
- `POST /drafts/{id}/review`
- `POST /drafts/{id}/approve`

#### 工作流

- `POST /systems/{id}/advance`
- `GET /systems/{id}/workflow`

### 异步规则

根据当前文档契约，Figure Plan、Manifest、Evidence Matrix、Outline、Section Draft、Vision 校验、数据分析等动作应统一异步返回任务句柄，而不是同步返回最终产物。这一规则已经在文档与架构设计中固定，但尚待完整落地。

## 开发指南

### 文档优先

本项目使用 `llmdoc/` 作为开发入口。开始任何实现前，建议至少阅读：

- `llmdoc/index.md`
- `llmdoc/overview/product.md`
- `llmdoc/overview/workflow-summary.md`
- 与当前任务相关的 `architecture/`、`reference/` 文档

### 本地开发建议

- 先启动基础设施，再运行 Alembic 迁移
- 先跑测试，再做较大改动
- 数据层与工作流层的不变式优先于界面行为
- 避免把“规划中的契约”直接当成“已实现功能”

### 常用命令

```bash
# 后端测试
python -m pytest backend/tests

# 后端 lint
python -m ruff check backend

# Alembic heads
python -m alembic -c backend/alembic.ini heads

# Alembic 升级
python -m alembic -c backend/alembic.ini upgrade head

# 前端开发
cd frontend && npm run dev && cd ..

# 前端类型检查
cd frontend && npm run typecheck && cd ..
```

## FAQ

### 这是一个通用 AI 论文生成器吗？

不是。它是一个实验体系驱动、证据约束、门禁推进的论文工作流平台。

### 当前可以直接用于真实论文生产吗？

还不建议。当前仓库主要用于架构验证、数据建模、工作流边界定义、前后端骨架开发与测试基线建设。

### 当前 README 里为什么既有“已落地基础”又有“规划中的契约”？

因为仓库当前处于 MVP 初始化阶段。为了帮助读者快速理解方向，README 同时展示了：

- 已经存在的骨架与基线
- 已经定义但尚未完整实现的目标契约
- 后续 Roadmap

### 为什么强调 Evidence Matrix？

因为项目将其定义为唯一事实源，草稿必须基于已确认 claims 与证据关系生成，而不是脱离实验事实自由扩写。

## Roadmap

近期重点：

- 完成单实验体系闭环 MVP
- 打通项目 / 体系 / 资产 / Evidence / Outline / Draft / Review 的端到端链路
- 把文档契约逐步落地为真实 API、Workflow 与前端交互
- 增强迁移、集成测试与端到端测试覆盖

中期方向：

- 完善审批与退回机制
- 提升资产与分析结果的可追溯性
- 完善任务托盘与长任务反馈体验
- 扩展多实验体系协同能力

## 贡献指南

欢迎通过以下方式参与：

- 提交 issue 描述问题或需求
- 提交 PR 改进实现、测试或文档
- 在开始较大改动前，先阅读 `llmdoc/` 并明确系统不变式

建议贡献流程：

1. 阅读 `llmdoc/index.md`
2. 明确目标与影响范围
3. 补充或更新测试
4. 保持代码、README 与 llmdoc 一致
5. 提交前运行测试与静态检查

## License

当前仓库尚未提供明确的开源许可证文件。

如果你计划对外开源，建议在根目录补充正式的 `LICENSE` 文件，并在此处同步声明。
