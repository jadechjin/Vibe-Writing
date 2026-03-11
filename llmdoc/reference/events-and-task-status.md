# 事件与任务状态契约

## WebSocket 事件外壳

```ts
interface TaskEvent {
  type: string
  taskId: string
  workflowId?: string
  projectId: string
  systemId?: string
  status: 'queued' | 'running' | 'waiting_user' | 'succeeded' | 'failed' | 'cancelled'
  progress?: number
  message: string
  timestamp: string
  payload?: Record<string, unknown>
}
```

## 推荐事件类型

- `task.created`
- `task.started`
- `task.progress`
- `task.waiting_user`
- `task.succeeded`
- `task.failed`
- `workflow.state_changed`
- `gate.blocked`
- `gate.passed`

## 前端消费规则

- 底部 StatusTray 订阅任务状态
- 与当前 `projectId`、`systemId` 关联事件优先展示
- 不允许因长任务展示全局阻塞遮罩
