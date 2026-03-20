# CLI Skeleton Generation Retry/Reopen Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 G0 骨架生成在手动关闭 CLI 后重复启动、以及失败后重新打开向导无法再次生成的问题。

**Architecture:** 以后端工作流为单轮生成真相源，每次 generate 请求只允许一次 CLI 调用；前端生成面板增加“本轮开始时间”边界，只消费本轮开始后的任务事件，避免历史失败事件污染新一轮状态机。

**Tech Stack:** FastAPI, SQLAlchemy, React, TanStack Query, Vitest, pytest

---

### Task 1: 锁定后端自动重试缺陷

**Files:**
- Modify: `backend/tests/modules/skeletons/test_skeletons_service.py`
- Modify: `backend/app/modules/skeletons/service.py`

**Step 1: 写失败测试**

- 新增测试，模拟 `_invoke_provider()` 第一次返回空输出。
- 断言：
  - 抛出 `AppException`
  - `asyncio.to_thread` 只调用一次
  - 不会发生第二次 sleep/retry

**Step 2: 运行失败测试**

Run:
```bash
pytest backend/tests/modules/skeletons/test_skeletons_service.py -q
```

Expected: 新测试失败，表明当前实现还在自动重试。

**Step 3: 写最小实现**

- 将 `PROVIDER_RETRY_ATTEMPTS` 收敛为单次执行语义。
- 删除 `_invoke_provider()` 中的自动重试循环，只保留单次调用和单次错误分类。

**Step 4: 运行测试确认通过**

Run:
```bash
pytest backend/tests/modules/skeletons/test_skeletons_service.py -q
```

Expected: 新旧测试全部通过。

### Task 2: 锁定前端旧失败事件污染缺陷

**Files:**
- Create: `frontend/components/gates/g0/GenerationPanel.test.tsx`
- Modify: `frontend/components/gates/g0/GenerationPanel.tsx`

**Step 1: 写失败测试**

- 测试一：存在历史 `task.failed` 事件时，点击“确认并生成”后不应立即出现“操作失败”。
- 测试二：本轮开始后收到新的 `task.failed` 事件时，应显示错误。

**Step 2: 运行失败测试**

Run:
```bash
npx --prefix frontend vitest run frontend/components/gates/g0/GenerationPanel.test.tsx --config frontend/vitest.config.ts
```

Expected: 至少第一条测试失败，证明当前面板会误消费历史失败事件。

**Step 3: 写最小实现**

- 为生成面板增加 `runStartedAt` 本地状态。
- 历史回放与实时订阅都增加“事件时间必须晚于本轮开始时间”的过滤。
- `retry` / `cancel` / `complete` 后重置本轮上下文状态。

**Step 4: 运行测试确认通过**

Run:
```bash
npx --prefix frontend vitest run frontend/components/gates/g0/GenerationPanel.test.tsx --config frontend/vitest.config.ts
```

Expected: 新测试通过，面板只对本轮事件响应。

### Task 3: 做跨层回归验证

**Files:**
- Review: `backend/app/modules/skeletons/service.py`
- Review: `frontend/components/gates/g0/GenerationPanel.tsx`
- Review: `frontend/hooks/useSkeletons.ts`
- Review: `frontend/contexts/WebSocketContext.tsx`

**Step 1: 运行定向回归测试**

Run:
```bash
pytest backend/tests/modules/skeletons/test_skeletons_service.py -q
npx --prefix frontend vitest run frontend/components/gates/g0/GenerationPanel.test.tsx --config frontend/vitest.config.ts
```

Expected: 全部通过。

**Step 2: 做跨层检查**

- 检查 UI -> WebSocket -> workflow event -> CLI 调用链是否仍然一致。
- 确认没有引入新的 response shape、没有破坏已有 `handle.workflow_id` 绑定逻辑。

**Step 3: 记录结果**

- 在最终说明中明确：
  - 自动重试已移除
  - 重新打开生成向导可再次发起生成
  - 旧失败事件不再污染新一轮
