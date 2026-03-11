# thesis-workflow-mvp

## Context

当前仓库是绿地项目，只有主设计文档 `论文写作系统_前后端改造方案_最终版_补充技术栈说明.md`，暂无可复用前后端实现。目标是把文档中的论文工作流方案落成单实验体系闭环 MVP，并拆成 Builder teammates 可无决策机械执行的并行任务。

## Locked Decisions

- 后端：FastAPI
- 工作流：Temporal 从 MVP 首版引入
- 门禁：G0–G5 六门禁
- Asset Manifest：独立持久化实体
- 长任务反馈：WebSocket
- Evidence 面板：双栏主视图
- 前端：Next.js
- Claude Code：受控执行器，不是系统主体

## MVP Flow

`项目创建 → 体系定义 → Figure Plan → 数据上传/分析 → Manifest → Evidence Matrix → Outline → Section Draft → Review / Approve`

## Invariants

1. Evidence Matrix 是唯一事实源。
2. Draft 只能基于已批准 claims 写作。
3. 生成类动作统一异步返回 `workflow_id` / `job_id`。
4. `POST /systems/{id}/advance` 只请求推进，真正推进由 gates + workflow 决策。
5. Manifest 必须可独立版本化。

## Fixed Gate Mapping

- G0 → `System_Defined`
- G1 → `Figure_Plan_Ready`
- G2 → `Data_Uploaded + Analysis_Ready`
- G3 → `Assets_Confirmed`
- G4 → `Evidence_Matrix_Ready + Outline_Ready`
- G5 → `Chapter_Approved`

## Work Breakdown

### Task 1 基础工程骨架与文档基线
范围：`infra/*`、`backend/pyproject.toml`、`frontend/package.json`、`scripts/*`、`backend/tests/conftest.py`、`.claude/team-plan/*`、`llmdoc/**/*`

### Task 2 后端公共契约与配置
范围：`backend/app/core/*`、`backend/app/common/*`

### Task 3 持久层基础设施
范围：`backend/app/persistence/*`、`backend/alembic/env.py`

### Task 4 项目与体系模型/迁移
范围：`backend/app/persistence/models/project.py`、`backend/app/persistence/models/system.py`、`backend/alembic/versions/001_project_system.py`

### Task 5 资产与 Manifest 模型/迁移
范围：`backend/app/persistence/models/asset.py`、`backend/app/persistence/models/manifest.py`、`backend/alembic/versions/002_assets_manifest.py`

### Task 6 Evidence / Draft / Workflow 模型/迁移
范围：`backend/app/persistence/models/evidence.py`、`backend/app/persistence/models/draft.py`、`backend/app/persistence/models/workflow.py`、`backend/alembic/versions/003_evidence_draft_workflow.py`

### Task 7 Projects / Systems 模块
范围：`backend/app/modules/projects/*`、`backend/app/modules/systems/*`

### Task 8 Assets 模块
范围：`backend/app/modules/assets/*`

### Task 9 Evidence 模块
范围：`backend/app/modules/evidence/*`

### Task 10 Drafts 模块
范围：`backend/app/modules/drafts/*`

### Task 11 Executors 适配层
范围：`backend/app/executors/*`、`workers/*`

### Task 12 Gates / Tasks / Temporal Workflows
范围：`backend/app/modules/gates/*`、`backend/app/modules/tasks/*`、`backend/app/workflows/*`

### Task 13 Realtime 与应用装配
范围：`backend/app/realtime/*`、`backend/app/api/router.py`、`backend/app/api/websocket.py`、`backend/app/main.py`

### Task 14 前端外壳、页面骨架与通用数据接入基础
范围：`frontend/app/*`、`frontend/components/layout/*`、`frontend/components/tasks/*`、`frontend/lib/*`、`frontend/hooks/useWebSocket.ts`

### Task 15 Dashboard / Projects / Systems 工作区
范围：`frontend/components/dashboard/*`、`frontend/components/systems/*`

### Task 16 Assets 工作区
范围：`frontend/components/assets/*`、`frontend/hooks/useAssetManifest.ts`

### Task 17 Evidence 双栏工作区
范围：`frontend/components/evidence/*`

### Task 18 Drafting / Gates 工作区
范围：`frontend/components/drafting/*`、`frontend/components/gates/*`、`frontend/hooks/useDraftSync.ts`

## Single Owner Hotspots

- `backend/app/common/*`
- `backend/app/persistence/base.py`
- `backend/app/persistence/session.py`
- `backend/app/persistence/types.py`
- `backend/alembic/env.py`
- `backend/app/api/router.py`
- `backend/app/api/websocket.py`
- `backend/app/main.py`
- `frontend/app/*`
- `frontend/lib/*`
- `frontend/hooks/useWebSocket.ts`
- `frontend/hooks/useAssetManifest.ts`
- `frontend/hooks/useDraftSync.ts`

## Execution Layers

- Layer 0: Task 1
- Layer 1: Task 2 + Task 14
- Layer 2: Task 3 + Task 11
- Layer 3: Task 4 + Task 5 + Task 6
- Layer 4: Task 7 + Task 8 + Task 9
- Layer 5: Task 10 + Task 15 + Task 16
- Layer 6: Task 12 + Task 17
- Layer 7: Task 13
- Layer 8: Task 18

## Verification

- 非法状态跳转失败
- `/systems/{id}/advance` 在门禁不满足时返回结构化 blocker
- 所有生成类接口立即返回任务句柄
- Temporal 支持等待用户 / 退回 / 重试 / 恢复
- Evidence 绑定可回溯
- WebSocket 可实时推送任务状态
- 跑通单实验体系闭环
