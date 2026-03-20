import { fireEvent, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { FigurePlanWorkbench } from "./FigurePlanWorkbench"
import { buildSystemDetail } from "../testFixtures"
import { createMutationHookResult, createQueryHookResult, renderWithQueryClient } from "../testUtils"
import * as figurePlanHooks from "../../../hooks/useFigurePlan"
import * as skeletonHooks from "../../../hooks/useSkeletons"

vi.mock("../../../hooks/useFigurePlan", async () => {
  const actual = await vi.importActual<typeof import("../../../hooks/useFigurePlan")>("../../../hooks/useFigurePlan")
  return {
    ...actual,
    useConfirmFigurePlan: vi.fn(),
    usePatchFigurePlan: vi.fn(),
    useDeleteFigurePlan: vi.fn(),
  }
})

vi.mock("../../../hooks/useSkeletons", async () => {
  const actual = await vi.importActual<typeof import("../../../hooks/useSkeletons")>("../../../hooks/useSkeletons")
  return {
    ...actual,
    useSkeleton: vi.fn(),
  }
})

const mockedUseConfirmFigurePlan = vi.mocked(figurePlanHooks.useConfirmFigurePlan)
const mockedUsePatchFigurePlan = vi.mocked(figurePlanHooks.usePatchFigurePlan)
const mockedUseDeleteFigurePlan = vi.mocked(figurePlanHooks.useDeleteFigurePlan)
const mockedUseSkeleton = vi.mocked(skeletonHooks.useSkeleton)

function buildPlan(overrides: Partial<figurePlanHooks.FigurePlanDetail> = {}): figurePlanHooks.FigurePlanDetail {
  return {
    id: "plan-1",
    systemId: "system-1",
    figureNo: "Fig1",
    title: "Primary figure",
    claimText: "Claim text",
    dataNeededJson: [],
    methodJson: {},
    acceptanceCriteriaJson: [],
    status: "pending",
    version: 1,
    sectionKey: "intro",
    skeletonVersion: 2,
    briefText: "Initial brief",
    briefConfirmedAt: null,
    dataQuestion: null,
    evidenceText: null,
    createdAt: "2026-03-14T00:00:00Z",
    updatedAt: "2026-03-14T00:00:00Z",
    ...overrides,
  }
}

function buildSkeletonDetail(
  overrides: Partial<skeletonHooks.SkeletonDetail> = {},
): skeletonHooks.SkeletonDetail {
  return {
    id: "skeleton-1",
    systemId: "system-1",
    version: 2,
    skeletonJson: {},
    changeSummary: null,
    sourceAssetIds: [],
    status: "confirmed",
    confirmedAt: "2026-03-14T00:00:00Z",
    createdAt: "2026-03-14T00:00:00Z",
    updatedAt: "2026-03-14T00:00:00Z",
    ...overrides,
  }
}

describe("FigurePlanWorkbench smoke coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedUseSkeleton.mockReturnValue(
      createQueryHookResult(buildSkeletonDetail()) as unknown as ReturnType<typeof skeletonHooks.useSkeleton>,
    )
    mockedUseConfirmFigurePlan.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof figurePlanHooks.useConfirmFigurePlan>,
    )
    mockedUsePatchFigurePlan.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof figurePlanHooks.usePatchFigurePlan>,
    )
    mockedUseDeleteFigurePlan.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof figurePlanHooks.useDeleteFigurePlan>,
    )
  })

  it("renders the unified plan list and filters unlinked plans", () => {
    mockedUseSkeleton.mockReturnValue(
      createQueryHookResult(
        buildSkeletonDetail({
          skeletonJson: {
            figure_framework: [
              { figure_id: " Fig1 ", title: "Primary figure" },
              { figure_id: "Fig2", title: "Backup figure" },
              { figure_id: "", title: "Ignored invalid" },
            ],
          },
        }),
      ) as unknown as ReturnType<typeof skeletonHooks.useSkeleton>,
    )

    renderWithQueryClient(
      <FigurePlanWorkbench
        systemId="system-1"
        sections={buildSystemDetail().sections}
        skeletonId="skeleton-1"
        plans={[
          buildPlan({ id: "plan-1", figureNo: "Fig1", title: "Primary figure" }),
          buildPlan({ id: "plan-2", figureNo: "Fig2", title: "Backup figure" }),
          buildPlan({ id: "plan-3", figureNo: "Unknown", title: "Unlinked figure" }),
        ]}
      />,
    )

    expect(screen.getByRole("button", { name: "全部 (3)" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "未关联 (1)" })).toBeInTheDocument()
    expect(screen.getAllByText("Fig1: Primary figure").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Fig2: Backup figure").length).toBeGreaterThanOrEqual(1)

    fireEvent.click(screen.getByRole("button", { name: "未关联 (1)" }))
    expect(screen.getAllByText("Unknown: Unlinked figure").length).toBeGreaterThanOrEqual(1)
  })

  it("opens the editor overlay and saves the updated figure plan draft", () => {
    const patchMutate = vi.fn((_variables, callbacks) => {
      callbacks?.onSuccess?.()
      callbacks?.onSettled?.()
    })
    mockedUsePatchFigurePlan.mockReturnValue(
      createMutationHookResult({ mutate: patchMutate }) as unknown as ReturnType<
        typeof figurePlanHooks.usePatchFigurePlan
      >,
    )

    renderWithQueryClient(
      <FigurePlanWorkbench
        systemId="system-1"
        sections={buildSystemDetail().sections}
        plans={[buildPlan()]}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "Open Figure Plan Editor" }))

    expect(screen.getByRole("dialog", { name: "编辑图表规划" })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Figure No"), { target: { value: "Fig1A" } })
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Updated figure" } })
    fireEvent.change(screen.getByLabelText("Claim Text"), { target: { value: "Updated claim" } })
    fireEvent.change(screen.getByLabelText("Brief Text"), { target: { value: "Updated brief" } })
    fireEvent.change(screen.getByLabelText("Section"), { target: { value: "results" } })

    fireEvent.click(screen.getByRole("button", { name: "Save Figure Plan" }))

    expect(patchMutate).toHaveBeenCalledWith(
      {
        planId: "plan-1",
        input: {
          figureNo: "Fig1A",
          title: "Updated figure",
          claimText: "Updated claim",
          briefText: "Updated brief",
          sectionKey: "results",
        },
      },
      expect.any(Object),
    )
    expect(screen.queryByRole("dialog", { name: "编辑图表规划" })).not.toBeInTheDocument()
  })

  it("deletes the selected plan and falls back to the next visible plan", () => {
    vi.stubGlobal("confirm", vi.fn(() => true))

    const deleteMutate = vi.fn((_planId, callbacks) => {
      callbacks?.onSuccess?.()
      callbacks?.onSettled?.()
    })
    mockedUseDeleteFigurePlan.mockReturnValue(
      createMutationHookResult({ mutate: deleteMutate }) as unknown as ReturnType<
        typeof figurePlanHooks.useDeleteFigurePlan
      >,
    )

    renderWithQueryClient(
      <FigurePlanWorkbench
        systemId="system-1"
        sections={buildSystemDetail().sections}
        plans={[
          buildPlan({ id: "plan-1", figureNo: "Fig1", title: "Primary figure" }),
          buildPlan({ id: "plan-2", figureNo: "Fig2", title: "Backup figure" }),
        ]}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "Delete Figure Plan" }))

    expect(deleteMutate).toHaveBeenCalledWith("plan-1", expect.any(Object))
    expect(screen.getAllByText("Fig2: Backup figure").length).toBeGreaterThanOrEqual(1)
  })
})
