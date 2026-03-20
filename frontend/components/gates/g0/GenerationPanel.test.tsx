import { act, fireEvent, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import GenerationPanel from "./GenerationPanel"
import { createMutationHookResult, createQueryHookResult, renderWithQueryClient } from "../testUtils"
import type { TaskEvent } from "../../../lib/websocket"
import * as skeletonHooks from "../../../hooks/useSkeletons"
import * as webSocketHooks from "../../../hooks/useWebSocket"

vi.mock("../../../hooks/useSkeletons", async () => {
  const actual = await vi.importActual<typeof import("../../../hooks/useSkeletons")>(
    "../../../hooks/useSkeletons",
  )
  return {
    ...actual,
    useBuildPrompt: vi.fn(),
    useGenerateSkeleton: vi.fn(),
    useSkeletons: vi.fn(),
  }
})

vi.mock("../../../hooks/useWebSocket", async () => {
  const actual = await vi.importActual<typeof import("../../../hooks/useWebSocket")>(
    "../../../hooks/useWebSocket",
  )
  return {
    ...actual,
    useWebSocket: vi.fn(),
  }
})

const mockedUseBuildPrompt = vi.mocked(skeletonHooks.useBuildPrompt)
const mockedUseGenerateSkeleton = vi.mocked(skeletonHooks.useGenerateSkeleton)
const mockedUseSkeletons = vi.mocked(skeletonHooks.useSkeletons)
const mockedUseWebSocket = vi.mocked(webSocketHooks.useWebSocket)

let currentEvents: readonly TaskEvent[] = []
let invalidateHandlers: Array<(event: TaskEvent) => void> = []

function buildEvent(overrides: Partial<TaskEvent> = {}): TaskEvent {
  return {
    type: "task.failed",
    taskId: "task-1",
    workflowId: "workflow-old",
    projectId: "project-1",
    systemId: "system-1",
    status: "failed",
    message: "旧失败事件",
    timestamp: "2000-01-01T00:00:00.000Z",
    payload: {},
    ...overrides,
  }
}

describe("GenerationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentEvents = []
    invalidateHandlers = []

    mockedUseSkeletons.mockReturnValue(
      createQueryHookResult([]) as unknown as ReturnType<typeof skeletonHooks.useSkeletons>,
    )

    mockedUseBuildPrompt.mockReturnValue(
      createMutationHookResult({
        mutate: vi.fn((_input, callbacks) => {
          callbacks?.onSuccess?.({
            prompt: "请生成骨架",
            provider: "claude",
            fileDir: "",
            fileList: [],
          })
        }),
      }) as unknown as ReturnType<typeof skeletonHooks.useBuildPrompt>,
    )

    mockedUseGenerateSkeleton.mockReturnValue(
      createMutationHookResult({
        mutate: vi.fn(),
      }) as unknown as ReturnType<typeof skeletonHooks.useGenerateSkeleton>,
    )

    mockedUseWebSocket.mockImplementation((options = {}) => {
      if (options.onInvalidate) {
        invalidateHandlers.push(options.onInvalidate)
      }
      return {
        connectionState: "open",
        events: currentEvents,
      }
    })
  })

  it("ignores stale failed events from previous runs when a new generation starts", () => {
    currentEvents = [
      buildEvent({
        taskId: "task-old",
        workflowId: "workflow-old",
        timestamp: "2000-01-01T00:00:00.000Z",
      }),
    ]

    renderWithQueryClient(
      <GenerationPanel systemId="system-1" onComplete={vi.fn()} onCancel={vi.fn()} />,
      { systemId: "system-1" },
    )

    fireEvent.click(screen.getByRole("button", { name: "构建提示词" }))
    fireEvent.click(screen.getByRole("button", { name: "确认并生成" }))

    expect(screen.getByText("Claude Code 生成中")).toBeInTheDocument()
    expect(screen.queryByText("操作失败")).not.toBeInTheDocument()
  })

  it("shows an error when the current run receives a new failed event", async () => {
    mockedUseGenerateSkeleton.mockReturnValue(
      createMutationHookResult({
        mutate: vi.fn((_input, callbacks) => {
          callbacks?.onSuccess?.({
            handle: {
              workflow_id: "workflow-new",
              job_id: "task-new",
              status: "queued",
            },
          })
        }),
      }) as unknown as ReturnType<typeof skeletonHooks.useGenerateSkeleton>,
    )

    renderWithQueryClient(
      <GenerationPanel systemId="system-1" onComplete={vi.fn()} onCancel={vi.fn()} />,
      { systemId: "system-1" },
    )

    fireEvent.click(screen.getByRole("button", { name: "构建提示词" }))
    fireEvent.click(screen.getByRole("button", { name: "确认并生成" }))

    const handler = invalidateHandlers.at(-1)
    expect(handler).toBeTypeOf("function")

    await act(async () => {
      handler?.(
        buildEvent({
          taskId: "task-new",
          workflowId: "workflow-new",
          message: "本轮执行失败",
          timestamp: "2999-01-01T00:00:00.000Z",
        }),
      )
    })

    expect(await screen.findByText("操作失败")).toBeInTheDocument()
    expect(await screen.findByText("本轮执行失败")).toBeInTheDocument()
  })
})
