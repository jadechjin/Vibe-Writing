# CLI 骨架生成重试与重开修复设计

**问题概述：**

G0 骨架生成当前有两个互相放大的缺陷：

1. 后端在 CLI 失败后会自动重试，因此用户手动关闭终端窗口时，会看到同一轮生成被再次拉起。
2. 前端生成向导会读取当前 system 的历史 WebSocket 事件；当上一轮生成已经写入 `task.failed` 后，下一次重新打开向导时，旧失败事件会被误认为是本轮失败。

最终用户感知为：

- 生成骨架时“强行关闭 CLI 后会重复启动”
- 三次都失败或关闭后无法再次唤起
- 必须重启项目才能恢复

---

## 目标

- 手动关闭 CLI 窗口时，本轮生成只失败一次，不再自动重试。
- 用户关闭失败弹窗或重新打开生成向导后，可以立即重新发起新一轮生成。
- 前端只响应“本轮生成开始之后”的任务事件，不再被旧失败事件污染。

---

## 根因分析

### 根因 1：后端存在 provider 自动重试

`backend/app/modules/skeletons/service.py`

- `PROVIDER_RETRY_ATTEMPTS = 2`
- `_invoke_provider()` 中用 `for attempt in range(...)` 包裹整个 CLI 调用
- 当 CLI 返回空输出、非零退出码或超时后，会再次调用 `_run_in_terminal()`

这意味着用户手动关闭终端，不会被视为“结束当前轮次”，而会触发后端再次拉起一个新的终端窗口。

### 根因 2：前端把旧事件当成新一轮结果

`frontend/components/gates/g0/GenerationPanel.tsx`

- `workflowId` 还没从 `generate` mutation 返回前，历史事件回放直接读取当前 `systemId` 的全部事件
- 实时订阅里只要 `!workflowId`，也会接受该 system 的任意 `task.failed` / `task.succeeded`

`frontend/contexts/WebSocketContext.tsx`

- 事件历史会保留最近 50 条，同一个 task 会去重，但不同 task 的失败事件会一直留在缓存里

所以只要上一轮失败事件还在缓存中，下一轮刚进入 `running`，就可能立刻进入 `error`。

---

## 设计方案

### 方案 A：后端去重试 + 前端只消费本轮新事件

这是推荐方案。

#### 后端

- 取消骨架生成 CLI 的自动重试。
- 保留现有错误分类：
  - 超时
  - 非零退出码
  - 空输出
- 任何一种失败都立即写入 workflow failure event 并结束当前轮次。

#### 前端

- 在用户点击“确认并生成”时记录一个本地开始时间戳。
- 仅消费满足以下条件的事件：
  - 事件属于当前 `workflowId`；或者
  - `workflowId` 尚未回填，但事件时间晚于本地开始时间，且属于当前 `systemId`
- 历史事件回放同样加上“开始时间下界”过滤。
- `retry` / `cancel` / `complete` 时清空本轮的 `workflowId`、错误信息和开始时间。

---

## 不采用的方案

### 只改后端

虽然能消除“重复拉起终端”，但旧失败事件污染仍在，用户重新打开向导仍可能立刻报错。

### 只改前端

虽然能缓解“重开即失败”，但后端自动重试仍会继续制造多个终端窗口，不符合预期交互。

---

## 数据流与边界

本次改动涉及 4 层：

```text
UI GenerationPanel
  → useGenerateSkeleton / WebSocket hook
  → backend skeleton service
  → provider CLI process
```

关键边界：

1. UI → 后端：
   - 发起一次 generate 请求，只应对应一轮 CLI 调用。
2. 后端 → CLI：
   - 进程退出即视为本轮已结束，不能隐式拉起第二轮。
3. WebSocket → UI：
   - UI 必须知道“哪些事件属于本轮，哪些只是历史残留”。

---

## 测试策略

### 后端

- 为 `_invoke_provider()` 新增测试：
  - 当第一次返回空输出时，应直接抛错，不再重试第二次。

### 前端

- 为 `GenerationPanel` 新增测试：
  - 历史失败事件存在时，重新发起生成不应立刻进入错误态。
  - 本轮收到新失败事件时，仍应正常显示错误。

---

## 预期结果

- 手动关闭 CLI：当前轮次失败一次，界面显示错误，不再自动弹出第二个终端。
- 点击“重试”或重新打开生成向导：可以正常开始新一轮。
- 旧失败事件不再导致“必须重启项目才恢复”。
