# G4 证据矩阵与提纲闭环设计逻辑的可执行方案研究

## 仓库关键文件清单

以下为我将优先检视的 **jadechjin/Vibe-Writing** 仓库关键文件（用于还原现状实现、数据模型与门禁校验逻辑，并据此提出 G4 的闭环改造方案）：

- `README.md`：项目定位、G0–G5 工作流与“不变式”（Evidence Matrix 唯一事实源、Draft 受控生成、门禁软回溯等）。
- `论文写作系统_前后端改造方案_最终版_补充技术栈说明.md`：中文顶层原则与“先证据链、后叙事”、Outline 必须绑定 asset id、工作流平台化边界等。
- `backend/app/common/enums.py`：门禁枚举、状态机与 G4 必要条件（Evidence_Matrix_Ready + Outline_Ready）。fileciteturn43file0L1-L1  
- `backend/app/modules/gates/service.py`：各 Gate 的 blocker 校验逻辑，尤其是 G4 对 claims、evidence-link、outline/binding 的通过标准。
- `backend/alembic/versions/002_assets_manifest.py`：资产与资产元数据、Manifest 的表结构与字段边界。
- `backend/alembic/versions/003_evidence_draft_workflow.py`：claims、claim_evidence_links、outlines、outline_asset_bindings、section_drafts 等核心闭环表结构与约束。
- `backend/app/persistence/models/skeleton.py`：G0 的 `StructureSkeleton`（含 `skeleton_json`、`source_asset_ids`、`version` 与确认状态）。
- `backend/app/persistence/models/evidence.py`：FigurePlan、AnalysisRun、Claim、ClaimEvidenceLink 等 G1–G4 的核心对象模型与版本字段。
- `backend/app/modules/evidence/service.py`：FigurePlan 与 Evidence Matrix 的生成/绑定逻辑（现状算法与可改造点）。  
- `backend/app/persistence/models/draft.py` + `backend/app/modules/drafts/service.py`：Outline 的版本化、confirm、binding，以及“仅基于 approved claims 生成”的写作约束机制。
- `backend/app/persistence/models/system.py` + `backend/app/persistence/models/project.py`：系统/项目可用的结构信息（`system_sections`、`thesis_schema_json` 等），用于判断“用户目标/风格/结构偏好”是否已有落点。
- `frontend/components/gates/EvidenceMatrixPanel.tsx`：G4 工作台前端交互顺序（生成矩阵→审查 claims→补证据/绑定→生成提纲→确认提纲）。

## 执行摘要

仓库现状已经具备“闭环的骨架”：数据层面用 `Claim` + `ClaimEvidenceLink` 表达“证据矩阵”，用 `Outline` + `OutlineAssetBinding` 表达“提纲与证据绑定”，门禁层面在 G4 校验“已批准 claims 且每个已批准 claim 至少有一个 evidence link，同时最新 outline 已确认且 bindings>0”。

但当前 G4 的**生成逻辑**仍偏“占位”：Evidence Matrix 的自动生成在 `system_sections` 与 `assets` 存在时，采用轮转方式把 asset 分配给 section 并生成一条 claim 语句，再创建 evidence link；Outline 的自动生成仅按 `section_ref` 对已批准 claims 分组输出最简结构。这会导致 G4 与前序工件（FigurePlan、AnalysisRun、Manifest、资产 QC/语义描述等）的“设计闭环”不够强：**前序产物没有被系统性映射为“可审查的论点—证据”—“可写作的结构”**，也缺少版本对齐、冲突检测与证据缺口的自动化提示。

本报告给出一套可落地方案：在 G4 引入“上下文快照（G4 Context Snapshot）+ 双向追溯规则”，把 G0–G3 的全部产物（结构骨架/章节、FigurePlan/brief、资产与 QC、Manifest、AnalysisRun 摘要/置信度等）统一汇聚为可计算输入；Evidence Matrix 生成以“FigurePlan/AnalysisRun/Manifest”驱动而非随机分配；Outline 生成以“已批准 claims + 证据强度 + 结构偏好”驱动，并确保每个 outline 节点可回指到 claims 与 assets，从而让“先证据链、后叙事”“Outline 必须绑定 asset id”“Draft 只能基于 approved claims 生成”的系统原则真正闭环。

## 闭环目标与现状诊断

仓库对系统目标的定义非常清晰：以“实验体系”为最小推进单元，采用 G0–G5 门禁推进；Figure Plan、Manifest、Evidence Matrix、Outline、Draft 等关键工件需要版本化、可审批、可追溯；并强调 **Evidence Matrix 是唯一事实源，Draft 只能基于已批准 claims 生成**。

从实现上看，闭环所需的关键“关系边”已经存在：  

- 证据层：`ClaimEvidenceLink` 连接 `Claim` 与 `Asset`，并可选连接 `AnalysisRun`（`analysis_run_id`）。fileciteturn46file0L1-L1  
- 大纲层：`Outline.generated_from_claims_json` 记录该提纲由哪些 claims 生成；`OutlineAssetBinding` 将某个 `section_key` 绑定到 `asset_id`。
- 门禁层：G4 blocker 明确要求“已批准 claims 必须有 evidence link”，且 outline 必须 confirmed 且 bindings>0。

问题集中在“**生成与对齐机制**”而非“数据表不存在”：  

- Evidence Matrix 的自动生成目前只验证“有 sections + 有 assets”，然后“每个 section 轮转拿一个 asset”并写入模板化 claim 语句；这并不保证 claim 与 FigurePlan/AnalysisRun/Manifest 的一致性，也无法体现证据强度差异与缺口。
- Outline 自动生成当前只是把 approved claims 按 `section_ref` 分组写入 `outline_json`（`{"sections":[{section_key, claim_ids}]}`），缺乏“论证顺序、证据引用点、冲突/缺口处理、版本对齐”。

因此，G4 的“闭环”需要从“结构化追溯”的角度补齐：类似软件工程中的 traceability matrix（矩阵记录开发过程产物间的关系），G4 也应提供“论点—证据—结构”多工件的双向追溯与覆盖度检查。同时，支撑可信写作的核心是 provenance（数据/工件由哪些实体、活动、人员产生，支持质量与可信度评估），这与 Evidence Matrix 的“可追溯证据链”目标一致。

G4输入输出与映射方案

### G4 输入清单

下表以“前序环节所有流程产出”为口径，标注仓库内是否已有明确落点；若无则标注“未指定”，并在后文给出默认假设与建议落点。

| 输入类别 | 来自Gate | 现有落点 | 说明 |
|---|---|---|---|
| 结构骨架（结构大纲/figure framework） | G0 | **已指定**：`StructureSkeleton.skeleton_json`、`version`、`source_asset_ids`、`status` | G0 通过条件要求存在 confirmed skeleton。 |
| 系统章节（section_key、标题、顺序） | G0→自动级联 | **已指定**：`SystemSection(section_key,title,order_no)` | Evidence Matrix/Outline 生成与校验都依赖 section_key。 |
| Figure/Table Plan（含 brief、与章节关联） | G1 | **已指定**：`FigurePlan(section_key,skeleton_version,brief_text,...)` | FigurePlan 可回写 skeleton 的 figure_framework（部分字段同步）。 |
| 资产（文件）与资产元数据（semantic_description、qc_status…） | G2/G3 | **已指定**：`assets` + `asset_metadata` | G3 校验要求 semantic_description 与 qc_status 通过。 |
| Asset Manifest（资产清单） | G3 | **已指定**：`AssetManifest(manifest_json,version,status)` | 建议在 G4 仅使用“最新 confirmed manifest”作为证据池。 |
| Analysis 结果（摘要、置信度、结构化指标） | G2 | **已指定**：`AnalysisRun(result_payload_json,summary,status,analysis_type,...)` | G2 校验要求 figure-plan-level analysis 覆盖。 |
| 事实卡片（Fact Cards） | G2/G3→G4 | **未指定** | 建议由 G4 自动从 AnalysisRun/AssetMetadata 抽取并沉淀为结构化“事实条目”。（见默认假设） |
| 引用（文献条目/DOI/URL/引用片段） | G0–G3 | **未指定** | 当前仅见 `asset_metadata.source_description` 字段可承载来源描述，但未形成引用对象模型。 |
| 用户目标（写作目标、受众、研究问题） | 项目/体系层 | **未指定**（现有 `ExperimentalSystem` 仅含 title、system_no、status） | 需扩展 project/system profile。（见默认假设） |
| 写作风格（语气、语言、篇幅、学术规范偏好） | 项目层 | **部分未指定**（存在 `Project.thesis_schema_json`，但语义未定义） | 建议在 `thesis_schema_json` 或新增 profile 中固化。 |
| 结构偏好（章/节结构、IMRaD、是否先图后文等） | 项目层 | **部分已指定**（README/中文方案强调“先图表与分析，后正文”） | 规则可写入生成器与校验器。 |

### G4 输出清单

| 输出类别 | 当前实现落点 | 关键用途 |
|---|---|---|
| Evidence Matrix（结构化呈现） | 由 `Claim` + `ClaimEvidenceLink` 共同表达 | 作为唯一事实源，驱动后续 Outline 与 Draft。 |
| 已批准 claims 集合 | `Claim.status="approved"` | Outline 生成仅依赖 approved claims。 |
| Outline（提纲） | `Outline(outline_json, generated_from_claims_json, version, status)` | 作为写作结构与 claims 选择器。 |
| Outline–Asset Bindings（章节→资产） | `OutlineAssetBinding(section_key, asset_id)` | 满足“提纲必须绑定 asset id”的产品原则，并作为 G4 通过条件之一。 |
| G4 通过信号 | 系统状态机 `Evidence_Matrix_Ready` + `Outline_Ready`，由 gate review 决定 | 门禁推进与阻塞项可视化。 |

### 闭环映射与绑定规则

为让 G4 与前序形成“设计闭环”，建议把 G4 拆成两个可计算的“绑定”问题，并用同一份 **G4 Context Snapshot** 贯穿：

**绑定问题 A：前序产物 → 证据矩阵（Claims & Evidence Links）**  

- `SystemSection` 为 claim 的“归属锚点”：每条 claim 必须有且仅有一个 `section_ref`，且该值必须存在于系统章节集合中（现有 approve 校验已做）。
- `FigurePlan(section_key, claim_text, brief_text)` 为 claim 的“候选生成器”：每个 plan 产出 1..N 条候选 claims，claim_id 建议稳定化（例如 `S{section_key}-F{figure_no}-{n}`），以减少回归时的“重复新 claim”。（现实现为 `C{index}`，可改造）
- `AssetManifest` 为证据资产池：Evidence Matrix 自动绑定证据时，只允许使用“最新 confirmed manifest”包含的资产（避免把未确认/低质资产引入事实源）。Manifest 本身是 G3 的通过条件之一。
- `AssetMetadata.semantic_description + qc_status` 决定证据可用性与强度基线：若 qc_status 未通过，则该资产可进入矩阵但必须标记为“弱/待补证据”，并触发缺口任务（见后文策略）。
- `AnalysisRun(summary, result_payload_json, confidence)` 决定证据强度的“技术加权”：若存在成功的 analysis run 且置信度/统计支持充分，则 evidence strength 上调；若缺失 run，则强度下调并生成补分析任务。

**绑定问题 B：证据矩阵 → 提纲（Outline Nodes & Bindings）**  

- `Outline.generated_from_claims_json` 必须等价于“本次提纲引用的 approved claims 集合”，并用于后续版本冲突检测（若 claim 集合变化，则 outline 视为过期）。
- `OutlineAssetBinding(section_key→asset_id)` 不应是纯手工补全：系统可基于“该 section 下证据强度最高/最具代表性的资产集合”自动建议绑定；用户只做确认/替换（降低维护成本）。当前前端已提供绑定入口与冲突提醒雏形。
- G4 gate review 需要从“存在性校验”升级为“覆盖度校验”：现状只要求 outline confirmed 且 bindings>0；建议升级为“每个 section 至少绑定 1 个资产 + 每个被提纲引用的 claim 至少 1 条 evidence link”，这样 Outline 才能保证写作阶段真正受证据约束。现状对 claims already enforce “approved claim must have evidence link”。

### 证据矩阵模板

下表为面向产品与运营的“证据矩阵视图模板”（可由 `assets / asset_metadata / claim_evidence_links / claims / analysis_runs` 聚合生成）。字段满足你的要求，并补充了落地时常用的“证据强度规则/责任动作”。

| 资产ID | 资产类型 | 内容摘要 | 支持论点 | 证据强度 | 引用来源（链接） | 可复用性 | 优先级 | 责任人/系统动作 |
|---|---|---|---|---|---|---|---|---|
| A-001 | image | SEM 图：颗粒形貌均一、粒径集中 | C-RESULT-01（“形貌均一”） | 强（QC=confirmed；有成功 analysis） | `https://example.com/assets/A-001` | 高（可复用到摘要/结果/小结） | P0 | 系统：从 analysis summary 抽取关键句；用户：确认 claim 表述 |
| A-002 | table | 指标对比表：处理组提升；含 p-value | C-RESULT-02（“显著提升(p<0.05)”） | 中（QC=confirmed；analysis 置信度一般） | `https://example.com/assets/A-002` | 中（主要用于结果章节） | P0 | 系统：提取统计支持到 `statistical_support`；用户：补充统计方法说明 |
| A-003 | pdf | 文献综述：相关工作与理论背景 | C-BG-01（“背景与研究缺口”） | 弱（仅文献来源；待补引用片段定位） | `https://doi.org/10.xxxx/xxxx` | 高（绪论/讨论可复用） | P1 | 系统：要求补齐引用定位（页码/段落）；用户：上传对应引用摘录资产 |

> 默认假设补充：若尚无“事实卡片/引用对象模型”，可先将“内容摘要”由系统从 `asset_metadata.semantic_description` 与 `analysis_run.summary` 生成；“引用来源”先复用 `asset_metadata.source_description` 或 DOI/URL 文本字段，后续再产品化为 citations 表。

## 提纲生成规则与闭环算法

### 提纲生成规则

在不改变现有表结构的前提下，建议将 `outline_json` 从“仅 sections/claim_ids”扩展为“可写作的层级节点”，但核心**闭环不变式**必须满足：  

- 任何 Outline 节点必须能回指到 **claim_ids**；任何 claim 必须能回指到 **至少一个 evidence link（asset_id，可选 analysis_run_id）**，这与 G4 gate 的设计方向一致。
- 任何 Draft 生成只能使用 approved claims，且 claims 必须属于目标 section（仓库后端已在 draft 生成校验中约束）。

具体规则（可执行）：

1. **章节骨架来源**：优先使用 `SystemSection(order_no)` 的顺序作为提纲一级目录；若 `Project.thesis_schema_json` 定义了章节模板（语义未指定），则以其覆盖默认骨架。
2. **节点粒度**：每个 section 下至少生成三个节点类型（可在 `outline_json` 中用 `node_type` 表达）：`background/method/result/summary`（若结构偏好未指定，则按实验型论文常用“引言—方法—结果—小结”的派生形式）。该结构与中文方案“按实验体系分章、章内固定骨架”的建议一致。
3. **claims 分配**：先按 `claim.section_ref` 分桶；桶内按证据强度排序（强→弱），再按 FigurePlan 顺序（若可推断）做稳定排序。claim 的 approved 集合来自仓库既有逻辑。
4. **资产绑定建议**：对每个 section，取该 section 下 claims 的 evidence links，按“证据强度×优先级”选 Top-K 作为 `OutlineAssetBinding` 建议候选；用户确认后写入 bindings。当前系统 bindings 已是 G4 通过条件之一。
5. **版本语义**：仓库现有 version 为整数自增（claims/outlines 等均有 version 字段与唯一约束）。建议在 `outline_json.meta` 中存 `snapshot_fingerprint` 与 `claim_versions`，用于“变更影响分析”。 版本号的语义可参考语义化版本的“变更影响”思想：当输入不兼容或结构变化时提升主版本，否则次版本/修订号递增。

### 算法流程图

```mermaid
flowchart TD
  A[汇聚G0–G3产物<br/>构建G4 Context Snapshot] --> B{输入完整性检查}
  B -- 缺SystemSection --> B1[阻塞:要求G0确认骨架/级联系统章节]
  B -- 缺Manifest或资产QC未通过 --> B2[阻塞:回到G3补齐manifest确认与asset_metadata/QC]
  B -- 缺AnalysisRun覆盖 --> B3[阻塞:回到G2触发分析任务/补数据]
  B -- 通过 --> C[生成候选Claims<br/>来源: FigurePlan.claim_text/brief + Analysis摘要]
  C --> D[候选Claims规范化<br/>去重/稳定claim_id/归属section_ref]
  D --> E[为每条Claim检索证据候选<br/>assets(来自confirmed manifest)+analysis_runs]
  E --> F[计算证据强度 & 证据缺口<br/>输出: ClaimEvidenceLinks草稿 + gap列表]
  F --> G[写入DB: Claim(version++)<br/>写入DB: ClaimEvidenceLink]
  G --> H[人审: 批准/退回Claims<br/>补充/替换证据链接]
  H --> I{G4校验: approved claims都具备evidence?}
  I -- 否 --> H
  I -- 是 --> J[生成Outline vN<br/>按section_ref分组+排序规则]
  J --> K[自动建议OutlineAssetBinding<br/>Top-K证据资产/每章至少1个]
  K --> L[人审: 调整提纲/确认绑定/确认Outline]
  L --> M{G4 Gate Review}
  M -- blockers --> N[输出阻塞原因<br/>定位回G2/G3/G4修复]
  M -- pass --> O[状态推进: Outline_Ready<br/>进入G5逐节写作]
```

### 伪代码

```text
function build_g4_snapshot(system_id):
  skeleton = latest_confirmed(StructureSkeleton)
  sections = SystemSection(order_no)
  plans = latest_by(figure_no)(FigurePlan)
  manifest = latest_confirmed(AssetManifest)
  assets = assets_in(manifest) with AssetMetadata
  runs = latest_succeeded(AnalysisRun) indexed by asset_id / figure_plan_id
  user_profile = project.thesis_schema_json.profile ?? DEFAULT  # 未指定则默认
  return {versions/fingerprint, skeleton, sections, plans, assets, runs, user_profile}

function generate_evidence_matrix(snapshot):
  candidates = []
  for plan in snapshot.plans where plan.status in {confirmed, approved}:
    candidates += derive_claims(plan, snapshot.runs, snapshot.assets)   # 1..N
  candidates = normalize_dedup_and_assign_section(candidates, snapshot.sections)
  for claim in candidates:
    evidence = rank_assets_for_claim(claim, snapshot.assets, snapshot.runs)
    if evidence.empty: register_gap(claim, reason="missing evidence")
    persist_claim_versioned(claim, status="draft")
    persist_claim_evidence_links(claim, evidence)
  return {claims, links, gaps}

function generate_outline(snapshot, approved_claims):
  if approved_claims.empty: raise blocker("no approved claims")
  outline = build_outline_nodes(snapshot.sections, approved_claims, snapshot.user_profile)
  bindings_suggestion = suggest_bindings(outline, approved_claims, snapshot.links)
  persist_outline_versioned(outline, generated_from_claims_json=approved_claim_ids, meta={fingerprint})
  return {outline, bindings_suggestion}
```

### 冲突检测、证据缺口识别与补充策略

**冲突检测（G4 内部自动化）**  

- **版本冲突/过期**：若 `snapshot_fingerprint` 与当前输入指纹不一致（例如 manifest version、skeleton version、assets/qc_status、analysis_run 最新成功结果变化），则将 Evidence Matrix/Outline 标记为“过期”，强制用户重新生成或“确认继续使用旧版本”。这是对 README 所述“软回溯：不回退状态但下次推进会重新校验”的机制补强。
- **证据不一致**：若 claim 的 evidence link 指向的 asset 不在最新 confirmed manifest 中，或 asset qc_status 未通过，则生成 blocker 并引导回到 G3。G3 通过条件与校验逻辑已在 gate service 中体现。
- **章节引用错误**：已批准 claim 的 `section_ref` 不存在于系统章节集合时，应禁止批准（现有后端已校验）并生成 blocker。

**证据缺口识别（用来“闭环回前序”）**  

- claim 无 evidence link：直接阻塞 G4（现有 gate 逻辑已阻塞）。
- section 无任何 approved claim：允许生成 outline skeleton，但该 section 必须产生“缺口任务”（如 `need_claims_for_section`），并在 UI 以红色 blocker 呈现，避免进入 G5 产生空写作。  
- evidence strength 低：不阻塞，但要求在 Outline 节点上标“弱证据”，并提供一键触发补分析（G2）或补资产 QC（G3）的行动按钮。

**补充策略（系统动作优先级）**  

1. 自动补链：若 FigurePlan 已绑定 assets 且存在成功 analysis run，系统优先把这些 assets 作为 evidence link 候选，减少人工选择成本。
2. 自动补分析：若 assets 已上传但 G2 分析覆盖不足，系统在矩阵页提供“触发分析”入口（现有后端已有 figure-plan analyze 的任务创建能力）。
3. 自动补引用：若资产类型为文献 PDF，系统先要求补齐“引用定位信息”（页码/段落/截图 asset），将其转化为可追溯 evidence（符合 provenance 目标）。

### 示例提纲

基于前述证据矩阵示例行（A-001/A-002/A-003），生成一个“实验体系章节”示例提纲（展示 claims 与 assets 的闭环绑定关系）：

- 引言（section_key: intro）  
  - 研究背景与相关工作（Claim: C-BG-01；Evidence: A-003）  
  - 本章研究问题与假设（Claim: C-BG-01；Evidence: A-003）  
- 结果与讨论（section_key: results_discussion）  
  - 形貌表征结果（Claim: C-RESULT-01；Evidence: A-001）  
  - 指标对比与统计显著性（Claim: C-RESULT-02；Evidence: A-002）  
  - 机制解释与局限（Claim: C-RESULT-01/02；Evidence: A-001/A-002；弱证据点需标注）  
- 本章小结（section_key: summary）  
  - 关键结论回顾（Claim: C-RESULT-01/02；Evidence: A-001/A-002）  
  - 对全文的贡献与下一步工作（承接后续系统章节）

> 说明：示例中的 section_key（intro/results_discussion/summary）在仓库内的实际 key 命名规则未明确给出，因此这里按“未指定”做了合理默认；真实落地应以 `SystemSection.section_key` 为准。

## 产品化落地与实施路线图

### 交互设计要点

现有 G4 面板已经呈现了“生成证据矩阵→审查/批准 claims→绑定证据→生成提纲→绑定资产→确认提纲”的正确顺序引导，这是闭环的基础。进一步产品化建议聚焦三件事：  

- **把“绑定关系”可视化为默认视图**：在 Claims 列表中默认展示其 evidence links（含 qc_status、analysis 置信度、来源），并支持“一键补链/替换”。目前 UI 仅提供选择 asset 创建 link，但未展示 link 质量结构。
- **把“闭环缺口”前置为行动项**：将 blocker 不仅作为门禁提示，还作为可操作任务列表（去 G2 触发分析、去 G3 补 QC、回 G4 改写 claim）。仓库 gate service 已能产生 blocker；需要前端将其转化为 CTA。
- **版本时间线与 diff**：由于 claims/outlines 等均版本化（带 version 字段），建议在 G4 提供“版本对比”：本次生成相对上次新增/删除/变更的 claims、绑定变化，以及输入指纹变化来源。

### 数据模型建议

在尽量复用现有表结构（claims/links/outlines/bindings）的前提下，补齐“闭环必须信息”：

- 新增 `g4_snapshots`（建议）  
  - 字段：`system_id, snapshot_id, fingerprint, skeleton_version, manifest_version, plan_versions, asset_versions, analysis_run_versions, created_at`  
  - 用途：判断 Evidence Matrix/Outline 是否过期，支撑冲突检测与回溯提示（与 README 的“软回溯重新校验”一致）。
- 扩展 `outline_json.meta`（兼容做法）：存 `{fingerprint, claim_refs:[{claim_id, version}], evidence_policy}`，避免立刻改表。
- 引用对象（未指定→建议新增）：`citations` + `citation_links`（claim↔citation、asset↔citation），把 `asset_metadata.source_description` 从自由文本升级为结构化引用，强化 provenance。

### 后端实现要点

- **Evidence Matrix 生成器重写**：把当前“轮转分配 asset→生成 claim”替换为“FigurePlan/AnalysisRun/Manifest 驱动的候选生成 + 自动补链 + gap 输出”。保留异步任务句柄与事件回写模式，符合仓库不变式。
- **Outline 生成器增强**：在现有“按 section_ref 分组”的基础上加入排序、节点类型、绑定建议与一致性校验；并在 confirm 前做覆盖度校验（每 section 至少 1 binding、每引用 claim 至少 1 evidence link）。
- **证据强度计算**：先做 rule-based（qc_status、analysis_run.status、analysis_confidence、asset_type 权重），后续再引入模型评估；计算结果写入 `ClaimEvidenceLink.statistical_support` 或新增聚合视图字段。
- **一致性校验器**：作为 G4 的“预提交钩子”，在 outline confirm 时检查 snapshot_fingerprint 与当前输入一致性，避免“确认了一个基于旧证据的提纲”。这种“变更影响分析”与 traceability matrix 的作用一致。

### 自动化程度建议

遵循仓库中文方案的定位：Claude Code/模型应作为“受控执行器”，而不是系统真相的维护者；因此建议“半自动 + 强审查”的自动化梯度：  

- 自动：候选 claims 生成、证据候选排序、绑定建议、缺口识别与任务化  
- 人审：claim 批准、关键证据确认、Outline 最终确认  
这与“门禁驱动而非自由对话驱动”“Evidence Matrix 唯一事实源”的原则一致。

### 关键 KPI

建议 KPI 围绕“闭环质量”而非“生成字数”：

- G4 一次通过率（首次生成后无需回退 G2/G3 的比例）  
- Claim 覆盖度（每 section 的 approved claim 数、每 claim 的 evidence link 数分布）  
- 证据强度分布（强/中/弱占比、弱证据滞留时间）  
- 提纲绑定覆盖度（每 section bindings≥1 的比例）  
- 从 G3→G4→G5 的平均耗时与返工率（软回溯触发次数）  
这些指标直接对应 gate 校验逻辑与“证据→写作”的闭环目标。

### 实施路线图表格

| 阶段 | 目标 | 关键交付物 | 自动化优先级 | 主要 KPI |
|---|---|---|---|---|
| 短期 | 让 G4 与 G0–G3 “强连接”，把缺口变成可操作任务 | Context Snapshot（fingerprint）、Evidence Matrix 生成器改造（基于 Manifest/Plan/Run）、G4 覆盖度校验 | 规则引擎 > LLM（先可解释） | G4 一次通过率↑、缺口闭环时间↓ |
| 中期 | 让 Outline 成为“可写作结构”并稳定版本演进 | Outline 节点层级化（node_type/claim_refs）、自动绑定建议、版本 diff、过期检测 | 半自动绑定/排序 | 绑定覆盖度↑、回滚/重做成本↓ |
| 长期 | 形成全链路 provenance 与跨体系整合能力 | citations/事实卡片对象化、跨体系证据复用、全局一致性检查与导出 | 自动化审查与建议增强 | “可追溯引用覆盖率”↑、导师审阅时间↓ |

> 备注：路线图与仓库 Roadmap 中“G4 workbench 精化、提升资产与分析结果可追溯性、完善审批与退回机制”的方向一致，但本报告将其具体化为“指纹快照+覆盖度校验+绑定建议+缺口任务化”的可实现工作包。
