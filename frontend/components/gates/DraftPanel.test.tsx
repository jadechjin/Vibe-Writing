import { fireEvent, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { DraftPanel } from "./DraftPanel"
import {
  buildBlocker,
  buildDraft,
  buildOutline,
  buildReviewComment,
  buildSystemDetail,
  buildWorkflowSnapshot,
} from "./testFixtures"
import { createMutationHookResult, createQueryHookResult, renderWithQueryClient } from "./testUtils"
import * as draftHooks from "../../hooks/useDrafts"
import * as evidenceHooks from "../../hooks/useEvidence"

vi.mock("../../hooks/useDrafts", () => ({
  useAddReviewComment: vi.fn(),
  useApproveDraft: vi.fn(),
  useDrafts: vi.fn(),
  useGenerateSectionDraft: vi.fn(),
}))

vi.mock("../../hooks/useEvidence", () => ({
  useOutlines: vi.fn(),
}))

const mockedUseDrafts = vi.mocked(draftHooks.useDrafts)
const mockedUseGenerateSectionDraft = vi.mocked(draftHooks.useGenerateSectionDraft)
const mockedUseApproveDraft = vi.mocked(draftHooks.useApproveDraft)
const mockedUseAddReviewComment = vi.mocked(draftHooks.useAddReviewComment)
const mockedUseOutlines = vi.mocked(evidenceHooks.useOutlines)

describe("DraftPanel smoke coverage", () => {
  const systemDetail = buildSystemDetail()
  const confirmedOutline = buildOutline({
    id: "outline-confirmed",
    version: 2,
    status: "confirmed",
    approvedAt: "2026-03-11T12:00:00Z",
    updatedAt: "2026-03-11T12:00:00Z",
  })

  beforeEach(() => {
    vi.clearAllMocks()

    mockedUseDrafts.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof draftHooks.useDrafts>)
    mockedUseOutlines.mockReturnValue(
      createQueryHookResult([confirmedOutline]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>,
    )
    mockedUseGenerateSectionDraft.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof draftHooks.useGenerateSectionDraft>,
    )
    mockedUseApproveDraft.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof draftHooks.useApproveDraft>,
    )
    mockedUseAddReviewComment.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof draftHooks.useAddReviewComment>,
    )
  })

  it("renders approved, needs-review, and ready-to-generate groups with required G5 fixture states", () => {
    const approvedDraft = buildDraft({
      id: "draft-approved",
      sectionKey: "intro",
      status: "approved",
      approvedAt: "2026-03-11T13:00:00Z",
      reviewComments: [
        buildReviewComment({
          id: "comment-approved",
          draftId: "draft-approved",
          decision: "approve",
          commentText: "Looks good to publish.",
        }),
      ],
    })
    const needsReviewOlderDraft = buildDraft({
      id: "draft-methods-v1",
      sectionKey: "methods",
      status: "approved",
      version: 1,
      updatedAt: "2026-03-11T11:00:00Z",
      approvedAt: "2026-03-11T11:00:00Z",
    })
    const needsReviewLatestDraft = buildDraft({
      id: "draft-methods-v2",
      sectionKey: "methods",
      status: "review_pending",
      version: 2,
      updatedAt: "2026-03-11T14:00:00Z",
      contentMd: "Methods draft preview",
      reviewComments: [
        buildReviewComment({
          id: "comment-methods",
          draftId: "draft-methods-v2",
          decision: "request_changes",
          commentText: "Need stronger justification.",
        }),
      ],
    })

    mockedUseDrafts.mockReturnValue(
      createQueryHookResult([
        needsReviewLatestDraft,
        approvedDraft,
        needsReviewOlderDraft,
      ]) as unknown as ReturnType<typeof draftHooks.useDrafts>,
    )

    renderWithQueryClient(
      <DraftPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Section_Drafting",
          currentGate: "G5",
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText("Chapter Drafting & Review")).toBeInTheDocument()
    expect(screen.getByText("Approved Sections")).toBeInTheDocument()
    expect(screen.getAllByText("Needs Review").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Ready to Generate")).toBeInTheDocument()
    expect(screen.getByText(/Looks good to publish\./)).toBeInTheDocument()
    expect(screen.getByText("Approve")).toBeInTheDocument()
    expect(screen.getByText("Request Changes")).toBeInTheDocument()
    expect(screen.getAllByText(/Preview is collapsed by default\./).length).toBeGreaterThanOrEqual(1)
    expect(
      screen.getAllByText(/No preview is available yet because this section does not have a latest draft\./).length,
    ).toBeGreaterThanOrEqual(1)
  })

  it("proves latest draft selection ignores array order and uses updatedAt as tie-breaker", () => {
    const newerSameVersion = buildDraft({
      id: "draft-intro-newer",
      sectionKey: "intro",
      status: "approved",
      version: 3,
      updatedAt: "2026-03-11T15:00:00Z",
      approvedAt: "2026-03-11T15:00:00Z",
      contentMd: "Newer intro draft",
    })
    const olderSameVersion = buildDraft({
      id: "draft-intro-older",
      sectionKey: "intro",
      status: "review_pending",
      version: 3,
      updatedAt: "2026-03-11T10:00:00Z",
      contentMd: "Older intro draft",
    })

    mockedUseDrafts.mockReturnValue(
      createQueryHookResult([newerSameVersion, olderSameVersion]) as unknown as ReturnType<
        typeof draftHooks.useDrafts
      >,
    )

    renderWithQueryClient(
      <DraftPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Chapter_Review",
          currentGate: "G5",
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText("Approved Sections")).toBeInTheDocument()
    expect(screen.getByText(/Approved: /)).toBeInTheDocument()
    expect(screen.queryByText(/Older intro draft/)).not.toBeInTheDocument()
  })

  it("keeps G5 generation blocked until authoritative draft truth arrives, even if websocket events are absent", () => {
    const generateDraftMutate = vi.fn((_variables, callbacks) => {
      callbacks?.onSuccess?.({ handle: { workflow_id: "wf-2", job_id: "job-2", status: "queued" } })
      callbacks?.onSettled?.()
    })

    mockedUseGenerateSectionDraft.mockReturnValue(
      createMutationHookResult({ mutate: generateDraftMutate }) as unknown as ReturnType<
        typeof draftHooks.useGenerateSectionDraft
      >,
    )

    const { rerender } = renderWithQueryClient(
      <DraftPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Section_Drafting",
          currentGate: "G5",
          latestEvent: null,
          events: [],
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    fireEvent.click(screen.getAllByRole("button", { name: "Generate Draft" })[0])

    expect(generateDraftMutate).toHaveBeenCalledTimes(1)
    expect(
      screen.getByText(/Draft generation has been queued\. This local success note clears when refreshed draft truth arrives\./),
    ).toBeInTheDocument()
    expect(screen.getAllByText(/No latest draft recorded for this section yet\./).length).toBeGreaterThanOrEqual(1)

    rerender(
      <DraftPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Chapter_Review",
          currentGate: "G5",
          latestEvent: null,
          events: [],
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(
      screen.getByText(/Draft generation has been queued\. This local success note clears when refreshed draft truth arrives\./),
    ).toBeInTheDocument()

    mockedUseDrafts.mockReturnValue(
      createQueryHookResult([
        buildDraft({
          id: "draft-intro-arrived",
          sectionKey: "intro",
          status: "review_pending",
          version: 1,
          updatedAt: "2026-03-11T16:00:00Z",
          contentMd: "Fresh draft after refresh",
        }),
      ]) as unknown as ReturnType<typeof draftHooks.useDrafts>,
    )

    rerender(
      <DraftPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Chapter_Review",
          currentGate: "G5",
          latestEvent: null,
          events: [],
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(
      screen.queryByText(/Draft generation has been queued\. This local success note clears when refreshed draft truth arrives\./),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/Claims used: 1 · Version 1/)).toBeInTheDocument()
  })

  it("keeps G5 disabled helper reasons local and prioritized", () => {
    mockedUseOutlines.mockReturnValue(
      createQueryHookResult([
        buildOutline({
          id: "outline-unconfirmed",
          version: 1,
          status: "draft",
          approvedAt: null,
        }),
      ]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>,
    )

    renderWithQueryClient(
      <DraftPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Section_Drafting",
          currentGate: "G5",
        })}
        blockers={[buildBlocker({ message: "Workflow blocker from backend." })]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(
      screen.getAllByText(/Generate draft is unavailable until the latest outline is confirmed in G4\./)[0],
    ).toBeInTheDocument()
  })
})
