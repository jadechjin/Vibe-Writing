# 本地开发指南

## 基础设施

MVP 本地依赖：

- PostgreSQL
- Redis
- MinIO
- Temporal

统一由 `infra/docker-compose.yml` 编排。

## 工程结构

- `frontend/`：Next.js
- `backend/`：FastAPI
- `workers/`：执行器/worker
- `infra/`：本地基础设施
- `scripts/`：辅助脚本

## 基础验证

1. 安装前后端依赖
2. 启动基础设施
3. 运行数据库迁移
4. 启动 FastAPI
5. 启动 Next.js
6. 运行测试与构建

## Windows Git Bash 注意事项

- 在当前项目的 Windows Git Bash 环境下，优先使用 `python` 或 `py -3` 执行 Trellis 脚本。
- 不要依赖 `python3`，因为它可能解析到 WindowsApps 的别名入口，并在脚本启动前直接以退出码 `49` 失败。
- 受影响的典型命令包括：
  - `python ./.trellis/scripts/get_context.py`
  - `python ./.trellis/scripts/task.py list`
  - `python ./.trellis/scripts/task.py archive <task-name>`
  - `python ./.trellis/scripts/add_session.py --title "..." --commit "-"`

## 前端验收基线（已落地）

- 采用 `Vitest + JSDOM + React Testing Library` 做 panel-level smoke，直接覆盖 `EvidenceMatrixPanel`（G4）与 `DraftPanel`（G5），不经过 MainShell 壳层。
- 运行命令：`npm --prefix frontend run test:smoke`
- 测试基础设施文件：
  - `frontend/vitest.config.ts` — Vitest 配置，JSDOM 环境
  - `frontend/vitest.setup.ts` — 导入 `@testing-library/jest-dom` matchers
  - `frontend/components/gates/testUtils.tsx` — QueryClient provider wrapper
  - `frontend/components/gates/testFixtures.ts` — contract-shaped fixture builders
- 已验证的关键语义：
  - deterministic latest-selection：version-first, updatedAt-second 排序
  - async truth split：202 Accepted ≠ artifact ready，websocket 可能缺失
- Playwright 仍可作为后续扩展验证路径，但当前不属于最小完成定义。

## 关键验证项

- 非法状态跳转失败
- 未满足门禁时 `/systems/{id}/advance` 返回 blocker
- `/systems/{id}/workflow` 的 snake_case 快照可被前端兼容层正确归一化
- `/systems/{id}/advance` 的顶层 camelCase / snake_case 混合响应可被前端兼容层正确归一化
- `normalizeWorkflowSnapshot` 优先依据 `current_state` 推导 `currentGate`，GateNav 与 Workbench 不出现刚过 gate 时的错位
- `useAnalysis.ts` 仅在资产上传 / metadata 修改后执行有限本地状态补丁，不扩大为通用乐观推进
- `useManifest.ts` 在 QC 确认后不做 G3→G4 乐观推进，只依赖查询刷新拿回真实 workflow 状态
- 生成类接口立即返回任务句柄
- Manifest 生成先返回 queued handle，再由后台任务落库并写回 succeeded/failed 事件
- WebSocket 可收到任务状态事件
- 前端 `npm run typecheck` 通过
- 前端 `npm run test:smoke` 通过（G4/G5 panel-level smoke）
