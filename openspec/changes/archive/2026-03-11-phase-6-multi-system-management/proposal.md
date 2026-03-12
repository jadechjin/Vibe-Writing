## Why

Phase 1-5 已完成单实验体系（System）的完整闭环（G0→G5），但当前系统仅支持单 System 推进。根据论文写作规范，用户需要完成至少 3 个独立实验体系章节后，才能进入绪论/结论的整合写作。因此需要支持多 System 并行管理能力。

## What Changes

- 项目级 Dashboard 展示所有 System 状态
- System 列表/创建/切换导航
- 项目完成度检测（至少 3 个 System 完成 G5）
- 前端路由支持多 System 切换
- 后端 API 扩展支持项目级聚合信息

## Capabilities

### New Capabilities
- `project-dashboard`: 项目级 Dashboard，展示所有 System 状态、完成度统计、Introduction 解锁状态
- `system-list-management`: System 列表展示、创建、删除、切换导航
- `project-completion-check`: 项目完成度检测逻辑，判断是否至少 3 个 System 完成 G5

### Modified Capabilities
<!-- 无现有 capability 的 requirement 变更 -->

## Impact

**后端**：
- `backend/app/modules/projects/`: 扩展 `GET /projects/{id}` 返回 `completedSystemCount` 和 `introductionUnlocked`
- `backend/app/modules/systems/`: 可能新增 `GET /projects/{id}/systems` 和 `DELETE /systems/{id}` 端点

**前端**：
- `frontend/app/projects/[projectId]/`: 新增项目 Dashboard 页面
- `frontend/app/projects/[projectId]/systems/[systemId]/`: 保持现有 System 工作台路由
- `frontend/components/`: 新增 SystemCard、SystemList、ProjectStats 组件
- `frontend/hooks/`: 新增 useProjectSystems、useCreateSystem、useDeleteSystem hooks

**数据模型**：
- 无数据库 schema 变更（Project 1:N System 关系已存在）
- 可能新增 `project_id + system_no` 唯一约束防止并发冲突
