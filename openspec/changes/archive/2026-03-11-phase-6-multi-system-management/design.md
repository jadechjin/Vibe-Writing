## Context

Phase 1-5 已完成单实验体系（System）的 G0→G5 完整闭环。当前系统仅支持单 System 推进，但论文写作规范要求用户完成至少 3 个独立实验体系章节后才能进入绪论/结论整合。

现有基础设施：
- 后端：`Project 1:N System` 关系已存在，`GET /projects/{id}` 已返回 `systems[]` 摘要
- 前端：`/projects/[projectId]` 页面已有基础 system 列表和创建表单
- 数据库：无 schema 变更需求

关键约束：不扩 Temporal 长流程，继续沿用 thin workflow + task event 模式。

## Goals / Non-Goals

**Goals:**
- 扩展 `ProjectDetail` 返回项目完成度指标（`completedSystemCount` + `introductionUnlocked`）
- 新增 `DELETE /systems/{id}` 受限删除端点
- 修复 `system_no` 并发分配竞争条件
- 新增前端项目级 Layout（WebSocket 提升 + 面包屑导航）
- 增强 Dashboard（SystemCard gate 进度可视化 + ProjectStats 完成度统计）
- 抽取 `deriveGateItems` 到共享 utility

**Non-Goals:**
- 不新增独立 Dashboard API 端点（扩展现有 `GET /projects/{id}` 即可）
- 不新增独立 `GET /projects/{id}/systems` 列表端点（现有 `ProjectDetail.systems` 已够用）
- 不实现绪论/结论跨体系整合写作（仅做解锁判定）
- 不实现 system 归档/软删除（受限删除即可）
- 不做 system 数量上限限制

## Decisions

### D1: 项目完成度 — 读时聚合 vs 持久化状态

**选择：读时聚合**

在 `projects/service.py` 的 `_build_project_detail` 中实时计算 `completedSystemCount`（`status == Chapter_Approved` 的 system 数量）和 `introductionUnlocked`（`completedSystemCount >= 3`）。

替代方案：在 Project 表加 `completed_system_count` 列，每次 system advance 时更新。
拒绝原因：引入写时一致性负担，且 system 数量有限（通常 3-5 个），读时聚合无性能问题。

### D2: System 删除 — 受限删除 vs 软删除

**选择：受限删除**

`DELETE /systems/{id}` 在执行前检查是否存在关联数据（assets / manifests / workflow events）。有数据则返回 `409 Conflict`，无数据则硬删除（CASCADE 清理 sections 等轻量关联）。

替代方案：软删除（加 `deleted_at` 列）。
拒绝原因：增加查询复杂度（所有查询需过滤），且当前阶段用户不太可能删除有数据的 system。

### D3: system_no 并发安全

**选择：唯一约束 + IntegrityError 映射**

现有 `(project_id, system_no)` 唯一约束已存在。在 `create_system` service 中捕获 `IntegrityError`，映射为 `409 Conflict` 并提示重试。

替代方案：SELECT FOR UPDATE 悲观锁。
拒绝原因：过重，且唯一约束已是最终防线，重试即可。

### D4: 前端 Layout 架构

**选择：新增 `frontend/app/projects/[projectId]/layout.tsx`**

职责：
1. 项目级 WebSocket 订阅（用 `projectId` 接收所有子 system 事件）
2. 面包屑导航（Projects → Project Name → System Name）
3. 共享容器样式

MainShell / ProjectWorkspace 保持不变，专注 G0-G5 工作台。

替代方案：不加 layout，每个页面独立管理。
拒绝原因：WebSocket 连接在页面切换时断开重连，面包屑无法共享状态。

### D5: SystemCard gate 进度

**选择：复用 `deriveGateItems` 逻辑**

将现有 system workbench 页面中的 `deriveGateItems` 函数抽到 `frontend/lib/gates.ts`，SystemCard 调用同一函数计算 gate 进度百分比（completedGates / 6）。

### D6: ProjectStats 完成度展示

**选择：基于 `ProjectDetail` 扩展字段**

前端 `ProjectStats` 组件直接消费 `projectDetail.completedSystemCount` 和 `projectDetail.introductionUnlocked`，不做额外计算。展示：完成进度条（X/3）、Introduction 解锁状态指示器。

## Risks / Trade-offs

**[R1] 受限删除可能让用户困惑** → 前端 409 错误时展示明确提示："该实验体系包含已有数据，无法删除。请先清理相关资产和工作流数据。"

**[R2] system_no 重试窗口** → 并发创建时 IntegrityError 后需要客户端重试。前端 `useCreateSystem` 的 `onError` 应提示用户重试，不做自动重试（避免循环）。

**[R3] 项目级 WebSocket 事件量** → 多 system 同时有后台任务时事件密集。前端对 `projectDetail` 查询的 invalidation 加 debounce（500ms），避免频繁 refetch。

**[R4] `GET /projects/{id}` 预加载膨胀** → 现有 repository 已全量加载 systems + sections。system 数量增多后查询变重。当前阶段可接受（通常 3-5 个 system），后续如需优化可加分页或 lazy load sections。
