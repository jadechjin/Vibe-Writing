# Team Research: 继续推进项目

## 增强后的需求

在不做新的架构决策前提下，继续推进当前 thesis workflow MVP 项目，为下一阶段 team-plan 产出零决策实现前的约束集与成功判据。范围聚焦于单实验体系闭环 MVP，目标不是补充信息清单，而是明确：当前仓库已经落地了什么、哪些只是契约与骨架、继续推进时哪些方向不能再考虑，以及后续实现顺序应如何受现有边界约束。

用户已确认的推进方向：

- 下一阶段首先落地：**后端最小闭环**
- MVP 中 Evidence Matrix 的持久化语义：**直接使用 `claims + claim_evidence_links` 表达，不新增独立 `evidence_matrices` 表**
- 第一批审批能力范围：**仅覆盖 Section Draft 审批**

## 约束集

### 硬约束

- [HC-1] 技术栈继续沿用当前已锁定方向：FastAPI + SQLAlchemy + Alembic + PostgreSQL + Redis + Temporal + MinIO + WebSocket，前端为 Next.js + React + React Query。不得在规划阶段引入新框架。— 来源：Codex / Gemini / llmdoc
- [HC-2] 当前目标仍是**单实验体系闭环 MVP**，不是整篇论文平台或多实验体系协同。— 来源：llmdoc / 用户
- [HC-3] 下一阶段优先落地 **后端最小闭环**，而不是先做前端工作台或先做泛化任务系统。— 来源：用户
- [HC-4] Evidence Matrix 在 MVP 中直接由 `claims + claim_evidence_links` 承担事实表达，**不新增独立快照表或显式 `evidence_matrices` 实体**。— 来源：用户
- [HC-5] 第一批审批能力仅覆盖 **Section Draft 审批**，`approval_tasks` 在 MVP 首轮不得扩张到 Figure Plan、Manifest、Outline 等全工件审批。— 来源：用户
- [HC-6] `POST /systems/{id}/advance` 只表达推进请求，真正推进必须由 gates 校验 + workflow 决策完成，不能直接改状态。— 来源：llmdoc / Codex
- [HC-7] 所有生成类动作必须异步执行并立即返回 `workflow_id` / `job_id` / `JobHandle`，不得同步返回最终产物。— 来源：llmdoc / Codex
- [HC-8] 固定门禁映射 G0–G5 与 `SystemState` / `GateRequirementKey` 枚举必须保留，不得自由改名或允许绕门禁跳步。— 来源：llmdoc / Codex
- [HC-9] 业务真相必须留在数据库与 workflow，不在 executor，也不在前端。— 来源：llmdoc / backend-modules / Codex
- [HC-10] `claim_evidence_links` 现有两条部分唯一索引与 `analysis_run_id` 的删除限制语义必须保持：当 link 仍引用某个 `AnalysisRun` 时，数据库必须拒绝删除该 `AnalysisRun`。— 来源：用户 / data-models / Codex
- [HC-11] Manifest 必须继续作为独立、可版本化实体，不能并回 asset 或 system card。— 来源：llmdoc / Codex
- [HC-12] Draft 必须只基于已批准 claims 写作；即便当前服务层未完全实现，该约束在 plan 阶段也不能被降级为可选。— 来源：llmdoc / Codex
- [HC-13] README 与 llmdoc 中列出的 API 清单应被视为**规划契约**，而不是现成已实现能力；下一阶段必须先补真正的后端模块与路由落地。— 来源：Codex / Gemini / README 复审
- [HC-14] 后端实现顺序必须遵守现有层次：先 common/persistence 之上的业务模块，再 workflow/realtime，再 API 装配；不能把核心业务逻辑直接堆进 router 或 placeholder workflow。— 来源：backend-modules / Codex

### 软约束

- [SC-1] 延续 Document-Driven Development：任何后续实现前，优先阅读 `llmdoc/index.md`、`llmdoc/overview/*` 及相关 architecture/reference 文档。— 来源：系统规则 / llmdoc
- [SC-2] 继续使用当前公共契约：`ApiResponse`、`TaskEvent`、`JobHandle`、`Blocker`、`GateReview`。— 来源：Codex / tests
- [SC-3] 前端当前仍是页面骨架与任务托盘壳层，因此下一阶段不应把前端页面完成度当作后端最小闭环的验收前提。— 来源：Gemini
- [SC-4] `/ws/tasks` 仍作为长任务反馈主通道；即使当前只是 bootstrap + heartbeat 样例，也应保持此端点作为兼容边界。— 来源：llmdoc / Gemini / Codex
- [SC-5] 继续沿用现有版本化与审计模式：核心工件通过 `version + audit fields` 提供可追溯基线。— 来源：data-models / Codex
- [SC-6] 当前阶段优先做最小可验证闭环，而不是提前抽象通用平台能力。— 来源：项目目标 / 用户选择

### 依赖关系

- [DEP-1] `common.enums/events/schemas` → `modules/* / workflows / realtime / api`：共享契约是所有后续实现的底层依赖。
- [DEP-2] `persistence/models + alembic` → `service/repository`：服务层必须以已存在 schema 和约束为边界，不能反向假设数据库结构。
- [DEP-3] `systems/assets/claims/claim_evidence_links` → `outline/section_drafts`：写作层依赖上游证据与 claims 事实表达。
- [DEP-4] `workflow_instances/workflow_events/approval_tasks` → `/systems/{id}/advance` 与 Draft 审批：推进与审批必须留下可追溯 workflow 记录。
- [DEP-5] HTTP 任务创建接口 → WebSocket `TaskEvent` 输出：异步句柄与实时状态必须成对设计，否则会出现“有 job handle、无真实状态反馈”的假异步。
- [DEP-6] Docker Compose 基础设施 → 本地联调：PostgreSQL / Redis / MinIO / Temporal 是继续推进后端最小闭环的外部依赖。

### 风险

- [RISK-1] 将 llmdoc / README 中的 API 契约误判为已实现 API，会导致下一阶段计划漏算大量后端模块与路由落地工作。— 缓解：明确区分“已落地基础”和“规划契约”。
- [RISK-2] `backend/app/modules/*` 目前仍为空包，若直接在 router 或 workflow 中堆逻辑，会破坏既定模块边界。— 缓解：按 `router/service/schemas/repository` 模板逐步补模块。
- [RISK-3] `system_workflow.py` 与 `broadcaster.py` 仍是 placeholder，过早暴露生成接口会形成“返回句柄但没有真实编排/广播”的假闭环。— 缓解：先做后端最小闭环中必要的 workflow / task / realtime 最小实现。
- [RISK-4] 当前测试主要覆盖 schema、契约和部分行为约束，尚未覆盖真实 gate 判定、workflow 推进与完整异步任务链路。— 缓解：后续计划必须显式包含这些测试补齐项。
- [RISK-5] 多张表同时保存 `project_id` 与 `system_id`，但缺少数据库级复合作用域校验，服务层若不主动校验，可能出现跨项目脏数据。— 缓解：把作用域一致性校验作为服务层硬要求。
- [RISK-6] llmdoc 的部分仓库现状描述仍带有早期绿地阶段信息，可能低估当前已落地基础。— 缓解：后续 plan 以实际代码 + 新版 README +相关 llmdoc 综合判断，不把旧表述当作唯一事实源。

## 成功判据

- [OK-1] 本地基线不被破坏：基础设施可启动、Alembic 可升级、FastAPI 可启动、`/ws/tasks` 可连接。
- [OK-2] 存在一个后端最小闭环，能围绕单实验体系推进核心状态，而不是只有空路由和占位 workflow。
- [OK-3] `/systems/{id}/advance` 在门禁不满足时返回结构化 blocker / review 信息，而不是直接修改系统状态。
- [OK-4] 当满足条件时，推进动作会留下可追溯的 `workflow_instances` 与 `workflow_events` 记录。
- [OK-5] 生成类动作表现为“立即返回 `JobHandle`，随后通过 WebSocket 推送任务状态变化”。
- [OK-6] Draft 审批是第一批真正落地的审批能力，并使用现有 `approval_tasks` / workflow 事实基础，而不是再引入新审批模型。
- [OK-7] Evidence Matrix 继续通过 `claims + claim_evidence_links` 表达，且数据库仍保持现有唯一性与删除限制语义。
- [OK-8] Draft / Outline 相关实现仍保留 `generated_from_claims_json` 等追溯字段，并在业务上只消费已批准 claims。
- [OK-9] 新实现不破坏现有 `ApiResponse`、`TaskEvent`、`JobHandle`、迁移与模型测试基线。

## 开放问题（已解决）

- Q1: 下一阶段首先落地哪条主链路？ → A: 后端最小闭环 → 约束：[HC-3]
- Q2: MVP 中 Evidence Matrix 采用什么持久化语义？ → A: 直接使用 `claims + claim_evidence_links`，不新增独立快照表 → 约束：[HC-4]
- Q3: 第一批审批能力先覆盖到什么范围？ → A: 仅 Draft 审批 → 约束：[HC-5]
