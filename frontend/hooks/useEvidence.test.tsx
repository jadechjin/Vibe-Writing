import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import type { PropsWithChildren } from "react"
import { vi, describe, expect, it, beforeEach } from "vitest"

import { useConfirmOutline, useGenerateEvidenceMatrix } from "./useEvidence"
import type { WorkflowSnapshot } from "./useProjectStatus"

const apiRequestMock = vi.fn()

vi.mock("../lib/api", () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
}))

function createWrapper(client: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe("useConfirmOutline", () => {
  beforeEach(() => {
    apiRequestMock.mockReset()
  })

  it("does not optimistically move workflow state to Outline_Ready on confirm success", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    const initialSnapshot: WorkflowSnapshot = {
      workflowId: "workflow-1",
      jobId: "job-1",
      projectId: "project-1",
      systemId: "system-1",
      workflowKey: "system_workflow",
      currentState: "Assets_Confirmed",
      currentGate: "G4",
      status: "waiting_user",
      context: {},
      version: 1,
      startedAt: "2026-03-17T00:00:00Z",
      completedAt: null,
      lastError: null,
      latestEvent: null,
      latestBlockers: [],
      events: [],
    }

    queryClient.setQueryData(["workflow", "system-1"], initialSnapshot)
    apiRequestMock.mockResolvedValue({
      id: "outline-1",
      systemId: "system-1",
      version: 1,
      outlineJson: { sections: [] },
      status: "confirmed",
      generatedFromClaimsJson: [],
      bindings: [],
      stalenessWarning: null,
      approvedAt: "2026-03-17T01:00:00Z",
      createdAt: "2026-03-17T00:00:00Z",
      updatedAt: "2026-03-17T01:00:00Z",
    })

    const { result } = renderHook(() => useConfirmOutline("system-1"), {
      wrapper: createWrapper(queryClient),
    })

    result.current.mutate("outline-1")

    await waitFor(() => {
      expect(apiRequestMock).toHaveBeenCalledWith("/outlines/outline-1/confirm", {
        method: "POST",
      })
    })

    const snapshot = queryClient.getQueryData<WorkflowSnapshot>(["workflow", "system-1"])
    expect(snapshot?.currentState).toBe("Assets_Confirmed")
    expect(snapshot?.currentGate).toBe("G4")
  })

  it("posts an explicit empty payload when generating the evidence matrix", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    apiRequestMock.mockResolvedValue({
      handle: {
        workflow_id: "workflow-1",
        job_id: "job-1",
        status: "queued",
      },
    })

    const { result } = renderHook(() => useGenerateEvidenceMatrix("system-1"), {
      wrapper: createWrapper(queryClient),
    })

    result.current.mutate({})

    await waitFor(() => {
      expect(apiRequestMock).toHaveBeenCalledWith("/systems/system-1/evidence-matrix/generate", {
        method: "POST",
        body: JSON.stringify({}),
      })
    })
  })

  it("passes forceRegenerate when explicitly requested", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    apiRequestMock.mockResolvedValue({
      handle: {
        workflow_id: "workflow-1",
        job_id: "job-1",
        status: "queued",
      },
    })

    const { result } = renderHook(() => useGenerateEvidenceMatrix("system-1"), {
      wrapper: createWrapper(queryClient),
    })

    result.current.mutate({ forceRegenerate: true })

    await waitFor(() => {
      expect(apiRequestMock).toHaveBeenCalledWith("/systems/system-1/evidence-matrix/generate", {
        method: "POST",
        body: JSON.stringify({ forceRegenerate: true }),
      })
    })
  })
})
