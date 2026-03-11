## Context

当前系统工作台只在 `/projects/[projectId]/systems/[systemId]` 路由下使用 `MainShell`，由 `SystemPage` 负责装配 `EvidenceHub`、`GatePanel` 与 `StatusTray`。底部 `StatusTray` 通过 `useWebSocket` 订阅 `/ws/tasks` 任务事件，并在 `task.succeeded` / `task.failed` 等事件到达时触发 workflow invalidation。

现状存在三个核心问题：

1. `useWebSocket` 每次调用都会创建独立连接，随着更多面板消费任务状态，重复连接会放大资源浪费和状态不一致风险。
2. `StatusTray` 只能显示任务状态 badge 和消息，缺少任务类型、进度百分比和直达相关 gate 的导航能力。
3. G1-G5 工作台面板虽然已经具备最小可操作闭环，但缺少贴近操作区的生成中状态反馈，用户必须盯着底部托盘才能知道异步任务是否仍在运行。

该变更不改动后端任务模型，也不扩展 workflow 编排。后端已通过 `TaskEvent` 提供 `type`、`status`、`progress`、`projectId`、`systemId` 等字段，前端应继续遵循“WebSocket 是长任务反馈主通道、Query Invalidation 负责回到后端真相”的边界。

## Goals / Non-Goals

**Goals:**
- 让系统工作台只维护一个共享 WebSocket 连接，避免重复订阅。
- 让 `StatusTray` 成为高信息密度但不吵闹的任务总览，补齐任务类型、进度百分比与 gate 导航。
- 在 G1-G5 gate 面板顶部展示与当前 gate 相关的活跃任务状态，让用户在操作点附近感知生成进度。
- 保持现有 `MainShell / ProjectWorkspace / GatePanel / StatusTray` 架构与 inline `CSSProperties` 风格，不引入平行状态管理模型。
- 保持 async truth split：202 Accepted 只表示任务已受理，不表示工件已经可用；最终展示仍以 query 刷新后的 authoritative state 为准。

**Non-Goals:**
- 不修改后端 API、WebSocket 协议或任务持久化结构。
- 不把所有 gate 内容改造成可自由切换的多标签工作台；本次只补“从任务导航到对应 gate”的最小交互能力。
- 不新增全局 loading mask、toast 中心、复杂动画系统或第三方 UI 依赖。
- 不重写 `GateNav`、`EvidenceHub` 或 MainShell 整体布局。
- 不尝试在本次设计里解决多系统页并发打开、跨页面共享事件历史等更大范围问题。

## Decisions

### 1. 用 `WebSocketProvider` 统一承载连接，而不是继续让 `useWebSocket` 自建连接

**Decision:**
新增 `frontend/contexts/WebSocketContext.tsx`，在系统页工作台范围内提供单一 socket 连接、最近事件列表和连接状态。`useWebSocket` 从“创建连接的 hook”重构为“消费共享上下文并按 `projectId` / `systemId` 过滤视图的 hook”。

**Rationale:**
- 一个工作台页会同时渲染 `StatusTray`、Gate 局部状态组件，以及未来可能新增的局部任务视图。继续一处一个 socket 是典型憨批设计，既浪费连接，也会造成事件历史不一致。
- 共享连接能让不同消费者看到同一份任务历史，避免某个组件因为挂载时机不同而错过近期事件。
- 保留 `useWebSocket(options)` API 形式，可以把改动控制在 hook 内部和 Provider 装配层，降低对现有组件的冲击。

**Alternatives considered:**
- 继续维持每组件独立连接：实现最省事，但扩展一个局部状态组件就多一条连接，后面必炸。
- 把事件流放进 React Query：不适合，因为 WebSocket 推送是流式增量，不是 query 语义；强拧进去只会把边界搞脏。

### 2. 任务到 gate 的归属使用前缀映射函数，不要求后端新增 `gateKey`

**Decision:**
新增 `frontend/lib/gateMapping.ts`，提供 `getGateKeyFromTaskType(type: string): GateKey | null`，按前缀规则映射：
- `figure_plan.*` → `G1`
- `analysis.*` → `G2`
- `manifest.*` → `G3`
- `evidence.*` → `G4`
- `draft.*` → `G5`

未知前缀返回 `null`，`StatusTray` 仍展示该任务，但不提供 gate 跳转。

**Rationale:**
- 当前后端契约已经稳定包含 `type`，而没有 `gateKey`。前端按前缀归类足以支撑本次范围，没必要为展示问题反向扩协议。
- 让未知类型降级为“仅展示不可跳转”比硬编码默认 gate 安全，避免误导导航。

**Alternatives considered:**
- 后端直接发送 `gateKey`：最直接，但会扩大改动面，不符合本次非目标。
- 前端完整枚举每一个具体任务类型：过度僵硬，后续新子类型一加就得改一堆映射。

### 3. `StatusTray` 仍然是任务总览区，但升级为“可读、可点、可定位”的紧凑列表

**Decision:**
增强 `TaskItem` 展示结构：状态 badge、任务类型 badge、消息文本、进度条、百分比文本、可点击容器。点击时如果映射到 gate，则通知 `SystemPage` 切换 `selectedGate`；否则保持只读展示。

**Rationale:**
- 状态 badge 解决“任务现在处于什么状态”，类型 badge 解决“这是哪类任务”，进度文本解决“还差多少”，三者缺一都会让用户瞎猜。
- 维持紧凑列表，而不是做成大卡片，能符合底部托盘空间限制和“美观简洁”的目标。
- 点击整行而不是单独放小按钮，交互命中更直接。

**Alternatives considered:**
- 只加进度条不加百分比：视觉上好看，但精度不够，用户照样一脸懵。
- 点击后弹模态框：信息更多，但导航问题没解决，还额外增加状态复杂度。

### 4. Gate 内联状态组件放在每个 gate panel 顶部，做成轻量级 `GateTaskStatus`

**Decision:**
新增 `frontend/components/gates/GateTaskStatus.tsx`，在 G1-G5 面板标题/说明区下方展示该 gate 的当前活跃任务。视觉采用小徽章 + 细进度条 + pulse 动画，仅在存在相关活跃任务时显示。

**Rationale:**
- 面板顶部最贴近用户当前操作目标，用户不用视线来回拉到底部看托盘。
- 轻量样式能强化状态存在感，但不会抢走主要操作区的注意力。
- 只显示当前 gate 相关任务，避免一个 panel 里塞满别的阶段状态把人看吐了。

**Alternatives considered:**
- 放在 panel 底部：存在感太弱，用户经常看不到。
- 做浮层或右上角悬浮信息：实现复杂，还容易和现有布局打架。
- 展示所有历史任务：噪音过大，不适合 panel 级提示。

### 5. 导航采用 `SystemPage` 层的 `selectedGate` 覆盖逻辑，不直接改 WorkflowSnapshot 真相

**Decision:**
在 `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx` 增加本地 `selectedGate` 状态，默认回退到 `snapshot.currentGate`。当用户点击 `StatusTray` 任务项时，如果任务可映射到某个 gate，则设置 `selectedGate`；当 workflow authoritative gate 发生刷新时，仅在 `selectedGate` 为空或失效时继续回退使用 snapshot。

`GatePanel` 接收新的 `selectedGate` prop，以该值优先决定展示哪个 gate 的工作区内容。`EvidenceHub` 是否同步跟随，取决于现有实现耦合度；本次最小范围允许只让右侧 workbench 先响应手动选择，但更推荐左右两栏保持同 gate 一致。

**Rationale:**
- 任务导航属于前端局部视图控制，不应该伪造或覆盖 workflow 真相。
- 通过覆盖层实现导航，能把“用户正在看哪个 gate”与“后端当前 authoritative gate 是什么”区分开，符合当前 mixed truth 处理模式。

**Alternatives considered:**
- 强行修改 workflow snapshot：污染服务端真相，属于错误分层。
- 只滚动页面不切 gate：当前页面布局没有多 gate 同时展开区域，滚动根本解决不了事。

### 6. 仍以 query invalidation 回到后端真相，WebSocket 只负责即时反馈

**Decision:**
保留现有 `onInvalidate(event)` 机制，继续在 `workflow.state_changed`、`gate.passed`、`gate.blocked`、`task.succeeded`、`task.failed` 到达时刷新 workflow query。`GateTaskStatus` 与 `StatusTray` 的即时视觉更新直接来自 WebSocket 事件，但一旦 authoritative query 回来，应以最新 snapshot 和各 feature query 结果清理过期本地状态。

**Rationale:**
- 当前系统已经验证过 async truth split：只有 query 刷新后的工件和 workflow 状态才可信。若把 WebSocket 事件直接当工件真相，迟早出脏状态。
- 保持这条边界，可以让本次改动只是增强可视化，而不是重写数据流。

**Alternatives considered:**
- 在 WebSocket 里直接推导 gate passed / artifact ready：太激进，和现有约束冲突。
- 完全依赖轮询不看 WebSocket：会损失即时反馈，用户体验倒退。

## Risks / Trade-offs

- **[共享 Provider 范围过大]** → 将 Provider 先限制在系统工作台页，而不是整个应用，避免把不需要任务流的页面也拖进来。
- **[未知 task type 无法映射 gate]** → `getGateKeyFromTaskType` 返回 `null` 时只展示不跳转，并在实现中保留易扩展映射表。
- **[手动 selectedGate 与 authoritative gate 感知冲突]** → 在 UI 上保留 workflow snapshot 信息，且仅把 `selectedGate` 当作视图覆盖；不要改写 workflow 数据。
- **[事件历史在 reconnect 后被清空造成局部提示闪断]** → 延续当前“重连清空事件列表”的策略，但通过 query invalidation 迅速回到后端真相；后续若用户确实介意，再单独规划重连持久化。
- **[面板顶部状态提示过于抢眼]** → 采用轻量徽章和小进度条，动画只对 running 状态启用，不做整块大闪烁。
- **[多个任务同时命中同一 gate 导致挤占空间]** → 初版仅展示最近的活跃任务或限制最多展示少量条目，避免把 panel 头部挤烂。

## Migration Plan

1. 新增 `WebSocketContext` 和 Provider，并在系统工作台页装配。
2. 重构 `useWebSocket` 为上下文消费者，保持外部调用签名尽量稳定。
3. 新增 `gateMapping` 辅助函数与 `GateTaskStatus` 组件。
4. 增强 `TaskItem` / `StatusTray`，接入任务类型、百分比和点击导航。
5. 在 `SystemPage` 与 `GatePanel` 中加入 `selectedGate` 覆盖逻辑。
6. 为映射、事件合并、gate 局部提示和导航行为补 smoke / unit tests。
7. 回归验证：`npm run typecheck`、`npm run test:smoke`。

**Rollback strategy:**
- 如果共享 Provider 引入不可接受的问题，可先回退到旧 `useWebSocket` 实现，同时保留 `TaskItem` 的纯展示增强。
- 如果 `selectedGate` 导航逻辑带来视图错乱，可临时关闭点击导航，仅保留信息展示，不影响底层任务流。

## Open Questions

- 当前实现阶段无阻塞性开放问题。
- 若后续发现 `TaskEvent.type` 命名不稳定，再单独评估是否要由后端补 `gateKey` 字段，但这不属于本次交付前置条件。
