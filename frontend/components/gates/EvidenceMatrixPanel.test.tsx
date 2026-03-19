import { fireEvent, screen, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { EvidenceMatrixPanel } from "./EvidenceMatrixPanel"
import {
  buildAsset,
  buildBlocker,
  buildClaim,
  buildOutline,
  buildOutlineBinding,
  buildSystemDetail,
  buildWorkflowSnapshot,
} from "./testFixtures"
import { createMutationHookResult, createQueryHookResult, renderWithQueryClient } from "./testUtils"
import * as analysisHooks from "../../hooks/useAnalysis"
import * as evidenceHooks from "../../hooks/useEvidence"
import * as systemAdvanceHooks from "../../hooks/useSystemAdvance"
import { ApiError } from "../../lib/api"

vi.mock("../../hooks/useEvidence", () => ({
  useApproveClaim: vi.fn(),
  useBatchApproveClaims: vi.fn(),
  useClaims: vi.fn(),
  useCreateClaimEvidenceLink: vi.fn(),
  useCreateOutlineBinding: vi.fn(),
  useEvidenceGaps: vi.fn(),
  useG4Snapshot: vi.fn(),
  useGenerateEvidenceMatrix: vi.fn(),
  useGenerateOutline: vi.fn(),
  useConfirmOutline: vi.fn(),
  useOutlines: vi.fn(),
  useRebuildG4Snapshot: vi.fn(),
}))

vi.mock("../../hooks/useAnalysis", () => ({
  useAssets: vi.fn(),
}))

vi.mock("../../hooks/useSystemAdvance", () => ({
  useSystemAdvance: vi.fn(),
}))

const mockedUseClaims = vi.mocked(evidenceHooks.useClaims)
const mockedUseOutlines = vi.mocked(evidenceHooks.useOutlines)
const mockedUseGenerateEvidenceMatrix = vi.mocked(evidenceHooks.useGenerateEvidenceMatrix)
const mockedUseApproveClaim = vi.mocked(evidenceHooks.useApproveClaim)
const mockedUseBatchApproveClaims = vi.mocked(evidenceHooks.useBatchApproveClaims)
const mockedUseCreateClaimEvidenceLink = vi.mocked(evidenceHooks.useCreateClaimEvidenceLink)
const mockedUseGenerateOutline = vi.mocked(evidenceHooks.useGenerateOutline)
const mockedUseConfirmOutline = vi.mocked(evidenceHooks.useConfirmOutline)
const mockedUseCreateOutlineBinding = vi.mocked(evidenceHooks.useCreateOutlineBinding)
const mockedUseAssets = vi.mocked(analysisHooks.useAssets)
const mockedUseG4Snapshot = vi.mocked(evidenceHooks.useG4Snapshot)
const mockedUseEvidenceGaps = vi.mocked(evidenceHooks.useEvidenceGaps)
const mockedUseRebuildG4Snapshot = vi.mocked(evidenceHooks.useRebuildG4Snapshot)
const mockedUseSystemAdvance = vi.mocked(systemAdvanceHooks.useSystemAdvance)

describe("EvidenceMatrixPanel", () => {
  const systemDetail = buildSystemDetail()
  const baseSnapshot = buildWorkflowSnapshot({
    currentState: "Assets_Confirmed",
    currentGate: "G2",
  })

  beforeEach(() => {
    vi.clearAllMocks()

    mockedUseClaims.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof evidenceHooks.useClaims>)
    mockedUseOutlines.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>)
    mockedUseAssets.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof analysisHooks.useAssets>)
    mockedUseG4Snapshot.mockReturnValue(createQueryHookResult(null) as unknown as ReturnType<typeof evidenceHooks.useG4Snapshot>)
    mockedUseEvidenceGaps.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof evidenceHooks.useEvidenceGaps>)
    mockedUseGenerateEvidenceMatrix.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useGenerateEvidenceMatrix>,
    )
    mockedUseApproveClaim.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useApproveClaim>,
    )
    mockedUseBatchApproveClaims.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useBatchApproveClaims>,
    )
    mockedUseCreateClaimEvidenceLink.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useCreateClaimEvidenceLink>,
    )
    mockedUseGenerateOutline.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useGenerateOutline>,
    )
    mockedUseConfirmOutline.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useConfirmOutline>,
    )
    mockedUseCreateOutlineBinding.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useCreateOutlineBinding>,
    )
    mockedUseRebuildG4Snapshot.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useRebuildG4Snapshot>,
    )
    mockedUseSystemAdvance.mockReturnValue(
      {
        ...createMutationHookResult(),
        advance: vi.fn(),
        advanceAsync: vi.fn(),
        data: null,
        isPending: false,
        isError: false,
        error: null,
        reset: vi.fn(),
      } as unknown as ReturnType<typeof systemAdvanceHooks.useSystemAdvance>,
    )
  })

  it("renders readiness summary and keeps local G5 advance blocked when blockers remain", () => {
    renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[
          buildBlocker({
            code: "section_missing_claims",
            message: "Some sections have no approved claims.",
            gate: "G2",
            currentState: "Assets_Confirmed",
            requiredChecks: ["Evidence_Matrix_Ready"],
            details: { sections: ["methods", "results"] },
          }),
          buildBlocker({
            code: "section_missing_binding",
            message: "Some sections have no outline binding.",
            gate: "G2",
            currentState: "Assets_Confirmed",
            requiredChecks: ["Outline_Ready"],
            details: { sections: ["methods", "results"] },
          }),
        ]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText("推进条件")).toBeInTheDocument()
    expect(screen.getByText(/章节 Approved Claims/)).toBeInTheDocument()
    expect(screen.getByText(/章节 Outline 绑定/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "推进到 G5" })).toBeDisabled()
    expect(screen.getByText(/当前无法推进：Some sections have no approved claims\./)).toBeInTheDocument()
  })

  it("enables the local G5 advance CTA when blockers are cleared", () => {
    const advance = vi.fn()
    mockedUseSystemAdvance.mockReturnValue(
      {
        ...createMutationHookResult(),
        advance,
        advanceAsync: vi.fn(),
        data: null,
        isPending: false,
        isError: false,
        error: null,
        reset: vi.fn(),
      } as unknown as ReturnType<typeof systemAdvanceHooks.useSystemAdvance>,
    )

    renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Assets_Confirmed",
          currentGate: "G2",
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    const button = screen.getByRole("button", { name: "推进到 G5" })
    expect(button).toBeEnabled()

    fireEvent.click(button)

    expect(advance).toHaveBeenCalledTimes(1)
  })

  it("keeps snapshot_stale advisory while allowing local advance", () => {
    const advance = vi.fn()
    mockedUseSystemAdvance.mockReturnValue(
      {
        ...createMutationHookResult(),
        advance,
        advanceAsync: vi.fn(),
        data: null,
        isPending: false,
        isError: false,
        error: null,
        reset: vi.fn(),
      } as unknown as ReturnType<typeof systemAdvanceHooks.useSystemAdvance>,
    )

    renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[
          buildBlocker({
            code: "snapshot_stale",
            message: "Outline is based on outdated data. Regeneration recommended but not required.",
            gate: "G2",
            currentState: "Assets_Confirmed",
            requiredChecks: ["Outline_Ready"],
            details: {},
          }),
        ]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    const button = screen.getByRole("button", { name: "推进到 G5" })
    expect(button).toBeEnabled()
    expect(screen.getByText(/建议刷新后重审/)).toBeInTheDocument()

    fireEvent.click(button)

    expect(advance).toHaveBeenCalledTimes(1)
  })

  it("prevents confirming outline before every section has a binding", () => {
    mockedUseOutlines.mockReturnValue(
      createQueryHookResult([
        buildOutline({
          id: "outline-1",
          status: "draft",
          bindings: [
            buildOutlineBinding({
              sectionKey: "intro",
            }),
          ],
        }),
      ]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>,
    )

    renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByRole("button", { name: "确认提纲" })).toBeDisabled()
    expect(screen.getByText(/还有 2 个章节未绑定资产/)).toBeInTheDocument()
  })

  it("prevents approving a claim without evidence links", () => {
    const createEvidenceLink = vi.fn()
    mockedUseCreateClaimEvidenceLink.mockReturnValue(
      createMutationHookResult({ mutate: createEvidenceLink }) as unknown as ReturnType<
        typeof evidenceHooks.useCreateClaimEvidenceLink
      >,
    )
    mockedUseClaims.mockReturnValue(
      createQueryHookResult([
        buildClaim({
          id: "claim-1",
          claimId: "claim-1",
          statement: "Need evidence first",
          sectionRef: "intro",
          status: "draft",
          evidenceLinks: [],
        }),
      ]) as unknown as ReturnType<typeof evidenceHooks.useClaims>,
    )
    mockedUseAssets.mockReturnValue(
      createQueryHookResult([buildAsset()]) as unknown as ReturnType<typeof analysisHooks.useAssets>,
    )

    renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByRole("button", { name: "批准 Claim" })).toBeDisabled()
    expect(screen.getByText(/需先补充至少 1 条证据链接后再批准/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/绑定证据资产/), {
      target: { value: "asset-1" },
    })
    fireEvent.click(screen.getByRole("button", { name: "创建证据链接" }))
    expect(createEvidenceLink).toHaveBeenCalledWith({
      claimId: "claim-1",
      input: { assetId: "asset-1" },
    })
  })

  it("shows conflict details and still offers a force-regenerate path when evidence matrix regeneration conflicts", () => {
    const mutate = vi.fn()
    mockedUseGenerateEvidenceMatrix.mockReturnValue(
      createMutationHookResult({
        mutate,
        error: new ApiError(
          409,
          "Cannot regenerate evidence matrix because latest approved claims or confirmed outline already exists",
          {
            code: "evidence_matrix_regeneration_conflict",
            details: {
              approved_latest_claim_count: 2,
              confirmed_outline_count: 1,
              sections_affected: ["intro", "results"],
            },
          },
        ),
        isError: true,
        status: "error",
      }) as unknown as ReturnType<typeof evidenceHooks.useGenerateEvidenceMatrix>,
    )

    renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText(/Evidence Matrix 生成失败/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "查看详情" })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "查看详情" }))

    const detailPanel = screen.getByText("重建冲突详情").closest("aside")
    expect(detailPanel).not.toBeNull()
    const panelQueries = within(detailPanel as HTMLElement)

    expect(panelQueries.getByText(/Approved Claims：2/)).toBeInTheDocument()
    expect(panelQueries.getByText(/Confirmed Outline：1/)).toBeInTheDocument()
    expect(panelQueries.getByText("intro")).toBeInTheDocument()
    expect(panelQueries.getByText("results")).toBeInTheDocument()
    expect(panelQueries.getByRole("button", { name: "去 Claims" })).toBeInTheDocument()
    expect(panelQueries.getByRole("button", { name: "去 Outline" })).toBeInTheDocument()
    expect(panelQueries.getByRole("button", { name: "去推进条件" })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "继续重建" }))

    expect(screen.getByText("强制重建证据矩阵")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "确认重建" }))

    expect(mutate).toHaveBeenCalledWith({ forceRegenerate: true })
  })
})
