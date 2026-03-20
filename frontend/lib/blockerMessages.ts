import type { Blocker } from "../hooks/useProjectStatus"

type BlockerDisplayInfo = {
  label: string
  detail: string
}

const BLOCKER_MESSAGES: Record<string, BlockerDisplayInfo> = {
  // G0
  skeleton_not_confirmed: {
    label: "结构骨架未确认",
    detail: "请在 G0 阶段上传模板文献并确认论文结构骨架。",
  },
  // G1
  figure_plan_not_ready: {
    label: "图表计划未确认",
    detail: "请确认所有图表计划的状态，包括简述与章节归属。",
  },
  no_figure_plan_images: {
    label: "图表计划缺少图片",
    detail: "请为已确认的图表计划上传实验图片。",
  },
  analysis_not_ready: {
    label: "数据分析未完成",
    detail: "请完成图片上传后的数据分析流程。",
  },
  analysis_incomplete: {
    label: "部分图表分析未完成",
    detail: "存在图表计划缺少分析结论或证据文本，请在 G1 分析面板中补充。",
  },
  // G2
  assets_not_confirmed: {
    label: "资产确认条件未满足",
    detail: "请在「资产审计」标签页中检查资产状态。",
  },
  figure_plan_missing_assets: {
    label: "图表计划缺少关联图片",
    detail: "存在图表计划尚未关联图片文件。请返回 G1 为对应图表计划上传图片后重新进入 G2。",
  },
  figure_plan_missing_evidence: {
    label: "图表计划缺少分析结论",
    detail: "存在图表计划尚未产生分析结论。请返回 G1 完成数据分析后重新进入 G2。",
  },
  approved_claim_sections_invalid: {
    label: "Claim 引用了无效章节",
    detail: "已批准的 Claim 的 section_ref 不属于当前体系章节列表。请在「证据与提纲」标签页中重新生成证据矩阵以修正。",
  },
  section_missing_claims: {
    label: "部分章节暂无已批准 Claim（非阻塞）",
    detail: "综述、讨论、结论等章节可能无需实证 Claim，不影响推进。如需补充，请在「证据与提纲」标签页点击「生成证据矩阵」。",
  },
  evidence_matrix_not_ready: {
    label: "部分 Claim 缺少证据链接",
    detail: "请在「证据与提纲」标签页的「Claims 审查队列」中，为已批准的 Claim 绑定对应的资产文件。",
  },
  outline_not_ready: {
    label: "提纲未就绪",
    detail: "请在「证据与提纲」标签页中，先批准足够的 Claim，然后点击「生成提纲」并完成确认。",
  },
  section_missing_binding: {
    label: "部分章节缺少提纲绑定",
    detail: "请在「证据与提纲」标签页底部的提纲列表中，为每个章节选择并绑定对应资产。",
  },
  snapshot_stale: {
    label: "数据快照已过期",
    detail: "提纲基于过时数据生成。建议在「证据与提纲」标签页中点击「刷新快照」后重新审核（非阻塞项，不影响推进）。",
  },
  // G3
  sections_missing_drafts: {
    label: "部分章节缺少草稿",
    detail: "存在章节尚未生成或验证草稿，请逐节完成草稿生成。",
  },
  sections_missing_traceability: {
    label: "部分草稿缺少溯源映射",
    detail: "存在草稿未建立与 Claim 的溯源关系，请检查后重新生成。",
  },
  chapter_not_approved: {
    label: "章节未通过审批",
    detail: "所有章节草稿需通过审批后才能完成当前门禁。",
  },
}

export function resolveBlockerDisplay(blocker: Blocker): BlockerDisplayInfo {
  const known = BLOCKER_MESSAGES[blocker.code]
  if (known) {
    let detail = known.detail
    // Enrich detail with dynamic data from blocker.details
    if (blocker.code === "assets_not_confirmed") {
      const manifestStatus = blocker.details.manifest_status as string | null | undefined
      if (!manifestStatus || (manifestStatus !== "confirmed" && manifestStatus !== "approved")) {
        detail = "Manifest 尚未确认。请在「资产审计」标签页中审核资产后点击「确认 Manifest」。"
      }
    }
    if (blocker.code === "analysis_incomplete") {
      const plans = blocker.details.unanalyzed_plans as string[] | undefined
      if (plans?.length) detail = `${plans.length} 个图表计划（${plans.join("、")}）缺少分析结论或证据文本。`
    }
    if (blocker.code === "figure_plan_missing_assets") {
      const nos = blocker.details.figure_nos as string[] | undefined
      if (nos?.length) detail = `${nos.length} 个图表计划（${nos.join("、")}）尚未关联图片文件。`
    }
    if (blocker.code === "figure_plan_missing_evidence") {
      const nos = blocker.details.figure_nos as string[] | undefined
      if (nos?.length) detail = `${nos.length} 个图表计划（${nos.join("、")}）尚未产生分析结论。`
    }
    if (blocker.code === "section_missing_claims") {
      const sections = blocker.details.sections as string[] | undefined
      if (sections?.length) detail = `以下章节暂无已批准 Claim：${sections.join("、")}。综述/讨论/结论类章节通常无需实证 Claim，不影响推进。`
    }
    if (blocker.code === "section_missing_binding") {
      const sections = blocker.details.sections as string[] | undefined
      if (sections?.length) detail = `以下章节缺少提纲绑定：${sections.join("、")}。请在「证据与提纲」标签页底部的提纲列表中为其绑定资产。`
    }
    if (blocker.code === "evidence_matrix_not_ready") {
      const count = blocker.details.claims_missing_evidence as string[] | undefined
      if (count?.length) detail = `${count.length} 条已批准 Claim 未关联证据链接。请在「证据与提纲」标签页的「Claims 审查队列」中为其绑定资产。`
    }
    if (blocker.code === "sections_missing_drafts") {
      const missing = blocker.details.missing_sections as string[] | undefined
      if (missing?.length) detail = `${missing.length} 个章节（${missing.join("、")}）尚未生成或验证草稿。`
    }
    if (blocker.code === "sections_missing_traceability") {
      const invalid = blocker.details.invalid_sections as string[] | undefined
      if (invalid?.length) detail = `${invalid.length} 篇草稿（${invalid.join("、")}）未建立溯源映射。`
    }
    return { label: known.label, detail }
  }
  return { label: blocker.code, detail: blocker.message }
}
