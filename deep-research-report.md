# 改进“数据与分析”模块的详细设计大纲

## 执行摘要

本设计旨在把系统的 **G2「数据与分析」模块**拉回“先图表与证据、后写作叙事”的初衷：对 **G1 用户上传的所有数据图（图片）**进行逐图、逐细节的结构化解析，并在用户点击任意图片时进入二级页面，执行“图像数据解构 → 文献/知识检索 → 证据映射 → 可写作复用的结构化输出”闭环，供下游写作模块稳定消费。当前仓库实现中，G1 已具备“素材图片”上传与缩略图展示能力（拖拽/点击上传，展示 `previewUrl` 缩略图），并通过后端对上传类型与大小进行约束（仅允许 `image/*`，且单文件限制 10MB）。fileciteturn28file0L1-L1 fileciteturn32file0L1-L1 但 G2 面板仍以“记录资产条目（fileName/storageKey）”为主，明确提示“当前接口记录资产条目而不是直接上传二进制文件”，且仅展示“分析任务状态”，缺少逐图解析与可追溯的分析结果结构。fileciteturn47file0L1-L1

为实现目标，本设计提出：以 **“每张图片=一个可重跑的 AnalysisRun（绑定 asset_id）”** 为核心数据单元，将逐图解析产物写入现有 `analysis_runs.result_payload_json`（并生成可读摘要 `summary`），与证据链（Claim–Evidence Matrix / 证据绑定）保持一致的可追溯性。fileciteturn38file0L1-L1 fileciteturn39file0L1-L1 二级页面侧，采用“先内部资源（启用连接器：GitHub，仅限仓库 jadechjin/Vibe-Writing）→ 再 Claude Code 中配置的 groksearch 学术搜索 → 再 Dify 知识库检索 → 必要时扩展到高质量外部来源（优先官方/原始论文，中文优先）”的检索顺序，最终生成带 DOI/URL 的引用证据与可写作复用输出。Claude Code 侧可用 headless/CLI 流式输出能力（`--output-format stream-json` 等），并可通过 MCP 接入外部工具，是承载 groksearch 的合理集成形态。citeturn6search0turn6search2turn7search0 Dify 侧建议使用其“知识库检索/召回 API（/datasets/{dataset_id}/retrieve）”返回可引用的 chunks（segments），再做证据映射与归因。citeturn13view0turn5search1

## 现状审阅与目标范围

### 现状与关键缺口

仓库的工作流定位为“实验体系驱动、证据约束、G0–G5 门禁推进”的论文工作流系统，并强调“图表与分析先于正文写作”“Evidence Matrix 是唯一事实源”。fileciteturn42file0L1-L1 fileciteturn34file0L1-L1 在 G1 阶段，前端已提供图片素材上传（拖拽/点击、多选），并以网格缩略图展示；后端在上传入口处限制“仅图片文件、10MB 内”，并为图片生成可预览的 presigned URL（`preview_url`）。fileciteturn28file0L1-L1 fileciteturn32file0L1-L1

然而，G2「数据与分析」面板目前主要是“登记资产条目 + 查看分析任务列表”，并明确说明不直接上传二进制文件；此外，面板也说明“不提供手动完成入口”，但后端 `create_analysis_run` 目前只创建工作流事件与 `analysis_runs` 记录，并不包含实际“逐图解析”的 worker 落地。fileciteturn47file0L1-L1 fileciteturn52file0L1-L1

### 功能目标

功能目标以“逐图、逐细节可追溯分析 + 二级页面证据化输出”为导向：

第一，自动枚举该 system 下所有 G1 上传的数据图（图片），并为每张图生成/更新“图像解析结果”（包含图表类型、结构要素、OCR 文本、数据点/数据表、置信度、坐标标注、异常检测与重建校验）。图片来源以 G1 FigurePlan 的 “source_image” 资产为主，并与系统资产（Asset）统一标识与可追溯关系。fileciteturn32file0L1-L1 fileciteturn39file0L1-L1

第二，主页面（G2）展示“逐图状态面板”：每张图的解析状态、置信度、是否需人工复核、最近一次解析时间、可复跑入口；并提供批量触发解析与增量更新（仅处理新增/变更图片）。

第三，二级页面（点击图片进入）执行“深度分析 + 证据检索融合”：充分使用 Claude Code 中的 groksearch 学术搜索，并接入 Dify 知识库，把“图片中的数据细节”转述为自然语言，可引用到写作模块；同时输出结构化数据表与引用文献（含 DOI/URL），并提供证据映射（Statement ↔ 引用 ↔ 图上位置/数据点）。

第四，输出结构必须稳定供下游写作模块消费：以 JSON schema 明确字段与接口契约，支持 Evidence Matrix、Outline、Draft 生成过程引用 `analysis_run_id` 与 `asset_id`。现有数据模型已允许 Claim–Evidence Link 绑定 `analysis_run_id`，可作为后续证据约束的核心挂钩。fileciteturn39file0L1-L1

### 非功能需求

性能方面，端到端解析耗时目标（P50/P95）、并发量（每 workspace/system 同时处理图片数）、以及可接受的“点击后二级页面首屏呈现时间”均为**未指定**；本设计将提供可运维的性能估算方法与缓存/队列方案，但最终阈值需产品/业务侧补齐。

隐私方面，需要明确：图片是否可能包含个人信息/敏感信息、跨境处理与第三方检索的合规边界、数据最小化、日志脱敏、保留策略等；若面向中国用户，应至少对齐《个人信息保护法》《数据安全法》关于合法、正当、必要、最小范围与安全保护义务的原则要求。citeturn9search1turn9search2（具体适用范围与合规口径：**未指定**）

可扩展性方面，应支持：后续接入更多图表类型、更多检索源、更多执行器（Vision 模型、Python 分析 worker、其他 Rerank/Embedding），并保持输出 schema 版本化与兼容性。

### 输入输出格式

输入侧：当前后端对 FigurePlan 图片上传的“显式约束”包括：MIME 类型需 `startswith("image/")`；单文件大小不得超过 10MB。允许的具体图片子类型（PNG/JPEG/TIFF/WebP/SVG 等）在服务端并未细化限制，因此为“**image/\***（具体子类型未指定）”。fileciteturn32file0L1-L1

输入元数据：至少需要 `system_id`、`figure_plan_id`（可选但建议）、`asset_id`、上传时间、上传者、图片 role（如 `source_image`）、以及可能的 figure_no/title/claim_text/section_key 上下文（提升检索质量）。其中 figure plan 上下文可由 G1 计划数据提供（仓库已有 Figure Plan 基础结构与 G1 工作流）。fileciteturn32file0L1-L1 fileciteturn34file0L1-L1

输出侧：以“可直接喂给写作模块”为标准，输出包含：自然语言描述、提取数据表、置信度、引用文献（带 DOI/URL）、原图标注坐标、处理日志（见下文 schema 表格）。建议写入 `analysis_runs.result_payload_json` 并同步简短摘要到 `analysis_runs.summary`。fileciteturn38file0L1-L1

## 用户流程与交互设计

### 主页面到二级页面的触发与反馈

主页面定位为 G2 的“逐图分析总览”，其核心交互从“资产登记”转为“图片队列 + 解析状态”：

触发条件一：用户进入 G2 面板时，系统拉取该 system 下“全部可分析图片清单”，并对缺失解析结果或解析过期（如图片变更哈希/版本变化）的条目自动入队（增量）。目前 G2 面板已集成 GateTaskStatus，可展示长任务进度与状态；新设计将扩展到“逐图任务”的进度呈现（例如每图一条轻量进度条，或聚合进度）。fileciteturn48file0L1-L1

触发条件二：用户点击“批量重新分析/仅分析新增”按钮时，对选定图片触发解析任务（异步），并在列表中即时显示“排队/运行/等待用户/成功/失败”。仓库既有 WebSocket 事件结构含 `status` 与可选 `progress`，适用于任务进度展示。fileciteturn49file0L1-L1

触发条件三：用户点击某张图片缩略图或列表项进入二级页面。二级页面默认先展示“已有解析结果（若存在）”，同时允许触发“深度检索增强”（groksearch + Dify）以生成更强的证据化描述。若无解析结果，则二级页面自动触发该图的解析任务，并展示逐步骤 loading 与可取消/重试。

加载与进度反馈：建议将解析管线拆分为稳定阶段（预处理、图表识别、OCR、数据提取、重建校验、检索、融合生成）并映射到 UI 的 stepper；对于不提供数值进度的阶段，沿用现有 GateTaskStatus 的 indeterminate 模式；若能提供百分比（例如按步骤权重计算），则填充 `progress` 字段。fileciteturn48file0L1-L1

错误处理：失败需可解释、可操作。至少区分：图片加载失败/权限问题、OCR 失败、图表类型不支持、数据点提取置信度低、外部检索超时/无结果、引用格式化失败。建议对每类错误提供“重试”“降级（仅 OCR+描述）”“人工校准/复核”入口。

可访问性要点：图片网格与二级页面必须支持键盘导航、可聚焦元素、可读的状态与进度语义。WCAG 2.2 已作为 W3C Recommendation 发布，建议以其“可感知、可操作、可理解、健壮”原则为基线；对弹窗/对话框/tooltip 等交互可参考 WAI-ARIA Authoring Practices 的键盘交互模式（如 Escape 关闭、Tab 在对话框内循环等）。citeturn8search6turn8search5

### 关键交互路径流程图

```mermaid
flowchart TD
  A[G1: 用户上传数据图(图片)] --> B[系统记录FigurePlanAsset/Asset并生成预览URL]
  B --> C[G2主页面: 数据与分析总览]
  C --> D{是否存在该图最新解析结果?}
  D -- 否 --> E[入队: 创建逐图AnalysisRun(queued)]
  D -- 是 --> F[展示解析摘要/置信度/状态]
  E --> G[异步执行: 预处理+识别+OCR+数据提取+校验]
  G --> H{置信度>=阈值?}
  H -- 否 --> I[标记needs_review + 生成可视化标注]
  H -- 是 --> J[写入result_payload_json + summary]
  F --> K[用户点击图片进入二级页面]
  I --> K
  J --> K
  K --> L{用户触发“证据增强”检索?}
  L -- 否 --> M[仅展示现有结构化解析与标注]
  L -- 是 --> N[检索顺序: GitHub仓库 -> groksearch -> Dify知识库 -> 外部高质量来源]
  N --> O[证据映射+引用格式化(含DOI/URL)]
  O --> P[生成写作可用的结构化输出包(JSON)]
  P --> Q[下游写作模块消费: 绑定asset_id/analysis_run_id]
```

## 图像分析流程

### 总体分层

本模块的“逐图逐细节分析”建议采用 **分层+可降级** 架构：先把图片解析为“可验证的结构化中间态”，再生成自然语言描述；当某层不稳定时，降级到上一层输出（例如“仅 OCR + 图表要素识别”，或“仅提供高置信数据表”），确保写作模块使用时不会被“幻觉式补全”污染证据链。

### 分步处理设计

图像预处理：对输入图片做统一规范化，包括分辨率标准化、去噪/去压缩伪影、倾斜矫正、色彩与对比度增强，以及必要时的裁剪（定位 plot area）。该步骤的输出应包含“预处理参数与可复现记录”，写入处理日志（用于复核与一致性）。

图表类型识别：对图片进行图表（或科学图像）类型判别。可按两级分类：一级为“是否为可结构化图表（bar/line/scatter/pie/box/heatmap/table-like）”；二级为具体子类型与组合（多子图、双轴、堆叠、分组、带误差棒等）。ChartOCR 等工作指出图表样式多样，纯规则法难覆盖，因此常见路径是“深度模型识别组件 + 规则推理还原”，并以中间态支撑泛化。citeturn0search0

数据点提取：针对不同图表类型采用不同提取策略（可并行尝试并以校验得分选最优）：

对于折线/散点/曲线：可用“图像分割/骨架化+曲线跟踪（autotrace）+坐标映射”的几何路径；也可用端到端视觉语言模型把图转表（plot-to-table）。DePlot 提出“把图像转为线性化表格，再由 LLM 推理”的范式，适合快速得到可用表格，但需额外做单位、刻度与误差验证。citeturn3view0

对于柱状图/箱线图等：可用检测柱体/箱体 bounding boxes、读取轴刻度与单位，然后计算数值；若存在误差棒，需要检测误差棒端点并映射到 y 轴。ChartOCR 的“组件检测 + 规则还原”范式对这些类型更可控，因为它强调“语义丰富的中间结果”。citeturn0search0

对于饼图/环图：检测扇区边界与中心角，结合图例/标签推断类别与占比；对于仅显示百分比的情形，仍需 OCR 与一致性校验（总和≈100%）。

置信度评估：建议把置信度拆为多维度而非单标量：

第一，视觉检测置信（组件检测/OCR 置信/数据点定位置信）。

第二，结构一致性置信（轴刻度单调、单位解析成功、类别-图例匹配、一致性约束如饼图总和、误差棒上下界关系等）。

第三，重建校验置信（见下文“可视化重建”）。

最终对写作模块输出一个“overall_confidence + 分项置信 + 可解释原因”。

异常检测：在提取到数据表后，以统计规则检测异常（例如：明显超出轴范围、误差棒为负、重复点、非预期离群）；同时结合领域上下文（figure plan 的 claim_text/section）识别“可能读错单位/对数轴误判”等结构性异常。异常应进入“needs_review”队列而非直接写入证据。

可视化重建：当需要保证“可验证”时，用提取出的数据与识别到的视觉样式（线型/颜色/图例）重绘简化版图表，并与原图做相似度对齐（例如 plot area 的关键像素差异、曲线轨迹重叠度）。重建校验是把“感知输出”变成“可验证输出”的关键一层：若重建明显偏离，应降低置信度并触发人工复核。交互式数据提取系统（如 ChartSense）也强调“半自动/交互式校正”能显著降低错误率并改善体验。citeturn0search1

### 可选算法/模型类别与取舍

深度学习+规则混合：以 ChartOCR 为代表，优点是能输出组件级中间态并用规则适配不同类型，利于可解释与可控；代价是工程复杂、需要为每类图维护规则与后处理。citeturn0search0

端到端图像到表格：以 DePlot 为代表，优点是快、对多类型图“先转表”可以统一下游；缺点是对复杂样式/双轴/多子图的稳定性与可验证性需要额外校验，且容易在坐标映射、单位解析上出错。citeturn3view0

交互式/半自动提取：以 ChartSense、WebPlotDigitizer 等工具形态为参照，优点是对复杂图的成功率高、适合低置信回退；缺点是需要用户投入校正成本，不适合全自动批量。citeturn0search1turn2search1

OCR 引擎选择：考虑中文场景与图表/文档混合场景，建议优先评估 PaddleOCR（支持多语言、并提供面向结构化解析的能力演进与文档/图表等复杂元素处理方向）。citeturn0search4turn0search5

## 检索与知识融合策略

### 检索顺序与边界

按你的约束，检索顺序必须明确且可扩展：

第一阶段：先使用所有启用连接器（列出：GitHub），且仅使用指定仓库 **jadechjin/Vibe-Writing**。本阶段的目标是：读取系统内既有“证据链、门禁、资产、分析 run”的数据契约与上下文，以生成更稳定的检索 query、提示词模板与证据约束规则。例如：仓库强调“图表与分析先于正文写作”“Evidence Matrix 唯一事实源”，以及 Vision 模块不应直接给出高层学术结论而应做图像级描述与规范校验，这些都应写入二级页面的生成约束（防止越权生成）。fileciteturn34file0L1-L1

第二阶段：使用 Claude Code 中配置的 **groksearch 学术搜索**。由于仓库已采用 Claude Code CLI 进行流式输出与会话续用（例如 `--output-format stream-json`、`--include-partial-messages`、`--resume` 等能力与模式），建议把 groksearch 作为 Claude Code 可调用的 tool（例如通过 MCP server 暴露一个 `groksearch.search` 工具），由“检索编排 Prompt”驱动其产生结构化文献结果。citeturn6search0turn6search2turn7search0

第三阶段：接入 Dify 知识库（RAG）。建议通过 Dify 知识库检索 API：`POST /datasets/{dataset_id}/retrieve`，以 query 检索最相关 chunks，并获取每个 chunk 的 `score` 与来源 document 信息，便于归因与证据映射；API Key 应仅保存在服务端，避免泄露。citeturn13view0

第四阶段：在前三阶段覆盖后，如仍缺乏关键证据，再扩展到其他高质量网络来源。优先级：官方文档与原始论文（arXiv/期刊 DOI）、中文权威来源优先；避免二手博客/聚合站作为唯一依据。在本设计中，图表理解/提取的关键原始论文可包括 ChartOCR、DePlot、ChartQA/PlotQA 等。citeturn0search0turn3view0turn3view1turn4view0

### groksearch 查询模板与召回-精确平衡

建议采用“两段式检索”：

第一段（召回优先）：从图像中抽取关键词集合 K（实验对象、指标名、单位、测量方法、材料/器件、统计方法、图标题/图例关键字），按中文优先组织 query，再补英文 query。模板例如：

- 中文：`{材料/对象} + {指标/表征方法} + {单位/测试条件} + (图表类型/统计方法)`  
- 英文：`{material/object} {measurement method} {metric} {unit} (dose-response OR time-course OR "bar chart")`

第二段（精确优先）：对第一段返回结果进行去重与聚类后，抽取高价值论文的“标题短语/方法名/指标组合”，使用短语引用、限定字段（title/abstract/DOI）以及年份窗口收敛，并增加否定词过滤（排除同名无关领域）。当图像 OCR 识别到标准术语（例如某些仪器型号、标准测试名），可直接加入精确约束提高 precision。

返回结构建议标准化为：`title/authors/year/venue/doi/url/abstract_snippet/confidence/relevance_tags`，并保留“检索链路日志”（每次 query、topK、过滤规则、最终入选原因）。

### Dify 知识库索引、语义匹配与证据映射

Dify 侧至少需要明确两类配置：

索引方式：建议在知识库侧选“高质量索引（Embedding）+ 可选 Rerank”，并把 `TopK` 与 `Score 阈值` 与模块置信系统打通（例如低分不用于写作证据，只用于背景参考）。Dify 文档对索引方式、TopK、Score 阈值与 Rerank 行为有明确说明。citeturn5search1turn5search0

检索 API：通过 `/datasets/{dataset_id}/retrieve` 获取 chunks（segments）与 score，并将 chunk 与图像解析的“细节单元（evidence unit）”进行映射：例如某条结论描述引用哪篇文献的哪段 chunk、支持哪一个数据点区间、对应图上哪个标注框。citeturn13view0

证据映射策略：以“细节单元”为中间枢纽。细节单元可以是：轴单位、图例类别、某个峰值、误差棒区间、趋势（上升/下降）、统计显著性标记等。每个单元都必须绑定图上坐标（bbox 或点集）与提取数据（若适用），再绑定 citation 列表（按优先级排序），确保“写作模块引用的一句话”能追溯到“图上哪里 + 引用哪里”。

## 输出规范与下游接口

### 输出总体原则

输出必须满足三点：结构化（机器可读）、可追溯（能回指 asset_id/analysis_run_id 与图上坐标）、可引用（文献带 DOI/URL 且有证据片段）。仓库现有数据结构已为 AnalysisRun 预留 `result_payload_json` 与 `summary` 字段，适合承载该输出包。fileciteturn38file0L1-L1

### 供写作模块使用的 JSON schema 字段表

下表以“点号路径（dot path）”描述嵌套字段；示例为缩略示例（真实输出可更完整）。

| 字段（dot path） | 类型 | 示例 | 说明 |
|---|---|---|---|
| schema_version | string | `"1.0.0"` | 输出包版本，便于写作模块兼容与迁移 |
| system_id | string | `"sys_123"` | 实验体系/系统 ID |
| figure_plan_id | string \| null | `"plan_456"` | 归属的 FigurePlan（若无法关联则为 `null`，并标注“未指定/未知”原因） |
| asset_id | string | `"asset_789"` | 原图资产 ID（写作/证据绑定的主键） |
| analysis_run_id | string | `"run_abc"` | 本次逐图解析对应的 AnalysisRun ID |
| image.mime_type | string | `"image/png"` | 输入图片类型；更细的类型限制若无则标注“未指定” |
| image.width_px / height_px | integer | `1920 / 1080` | 像素尺寸（用于坐标归一化） |
| image.source_url | string \| null | `"https://...presigned..."` | 可选：仅用于展示；若安全策略不允许则为 `null`（未指定） |
| extraction.chart_family | enum | `"line"` | 图表大类：`line/bar/scatter/pie/box/heatmap/table/unknown` |
| extraction.chart_subtype | string \| null | `"grouped_bar_with_errorbar"` | 子类型；无法稳定判断时为 `null` |
| extraction.ocr.text_blocks[] | array<object> | `{text:"Intensity", bbox:{...}, conf:0.93}` | OCR 文本块列表（含 bbox 与置信度） |
| extraction.axes.x / y | object | `{label:"Time", unit:"s", scale:"linear"}` | 轴信息（含单位、刻度类型） |
| extraction.legend.items[] | array<object> | `{name:"Control", color:"#..."}` | 图例解析结果（颜色/样式可选） |
| extraction.data.tables[] | array<object> | `{name:"series_1", columns:["x","y"], rows:[[0,1.2],...]}` | 提取出的数据表（支持多序列、多表） |
| extraction.data.points[] | array<object> | `{series:"Control", x:0, y:1.2, img_xy:{x:0.34,y:0.62}, conf:0.88}` | （可选）逐点列表，含数据值与图上坐标 |
| extraction.anomalies[] | array<object> | `{type:"out_of_range", message:"y超出轴范围", severity:"high"}` | 异常检测输出 |
| reconstruction.enabled | boolean | `true` | 是否执行重建校验 |
| reconstruction.similarity | number | `0.91` | 重建与原图的一致性得分（定义需版本化） |
| confidence.overall | number | `0.84` | 总置信度（0-1） |
| confidence.breakdown | object | `{ocr:0.9, geometry:0.8, consistency:0.85}` | 分项置信（便于人工审核） |
| narrative.summary_cn | string | `"图中显示…总体呈上升趋势…"` | 面向写作的中文摘要（必须可引用、可追溯） |
| narrative.detail_cn | string | `"在0–10 s区间…峰值约为…（见图中标注A）…"` | 更细粒度自然语言描述（建议分段结构） |
| evidence_units[] | array<object> | `{id:"eu_1", type:"peak", bbox:{...}, linked_data_refs:[...], claim_text:"峰值约为…"}` | “细节单元”列表：每个单元是证据映射与写作引用的最小单位 |
| citations[] | array<object> | `{id:"c1", title:"DePlot…", doi:"10.48550/arXiv.2212.10505", url:"https://arxiv.org/abs/2212.10505"}` | 引用文献列表（必须含 DOI 或 URL 至少其一） |
| citations[].snippets[] | array<object> | `{source:"dify_chunk", text:"...", locator:"docX#seg12"}` | 支撑片段（来自 groksearch 或 Dify chunk），用于归因 |
| evidence_map[] | array<object> | `{evidence_unit_id:"eu_1", citation_ids:["c3"], rationale_cn:"用于解释…方法学依据"}` | 证据映射：细节单元↔引用↔理由 |
| annotations.bboxes[] | array<object> | `{label:"x_axis_label", x0:0.12,y0:0.88,x1:0.42,y1:0.95}` | 原图标注框（建议归一化 0-1 坐标） |
| annotations.polylines[] | array<object> | `{label:"series_curve", points:[{x:0.1,y:0.2},...]}` | 曲线/轨迹标注（可选） |
| logs.pipeline[] | array<object> | `{step:"ocr", tool:"PaddleOCR", version:"3.x", duration_ms:1234, status:"ok"}` | 处理日志（可审计、可复现） |
| logs.retrieval[] | array<object> | `{stage:"groksearch", query:"...", topk:20, kept:6}` | 检索日志（避免记录敏感原文，保留必要元数据） |
| status.review_state | enum | `"auto_pass" \| "needs_review" \| "rejected"` | 输出包审核状态（用于门禁与写作可用性控制） |

### 下游接口建议

写作模块读取方式建议“双通道”：

其一，通过 `analysis_run_id` 读取最新结果包（用于证据链追溯与版本管理）。

其二，通过 `asset_id` 查找对应最新成功解析的 `analysis_run_id`（便于从资产清单出发）。仓库现有 Claim–Evidence Link 支持绑定 `analysis_run_id` 与 `asset_id`，可直接用来把“写作引用”落到可追溯证据上。fileciteturn39file0L1-L1

## 质量控制、人工复核与隐私合规

### 自动校验规则与阈值

阈值（如 overall_confidence ≥ 0.85 自动通过、0.6–0.85 需要抽检、<0.6 必须人工复核）为**未指定**；但建议至少落地以下自动校验：

结构一致性：轴刻度解析成功、单位非空/可解释、legend 与序列数匹配、饼图总和≈100%、误差棒上下界一致等。

重建一致性：重建相似度低于阈值 → needs_review（阈值未指定）。

引用有效性：每条对外“方法/解释性”陈述至少关联一个 citation；citation 必须有 DOI 或 URL；对 DOI 可做格式校验（不要求在线解析，但建议异步校验）。

证据优先级：优先使用原始论文/官方文档；若仅有二手来源则降级为“背景参考”，不得作为“结论性证据”。

### 需要人工审核的情形与审核界面要点

必须人工审核的典型情形：图表类型 unknown、多子图无法拆分、OCR 命中率低/关键单位缺失、坐标映射不稳定（疑似对数轴/双轴误判）、重建相似度低、异常检测高风险（例如数值超出轴范围）。ChartSense 等研究建议在自动提取后提供交互式纠偏以提升效率与准确性；WebPlotDigitizer 的产品形态也证明“校准轴→半自动提取→导出”的交互流程对复杂图有效。citeturn0search1turn2search1

审核界面要点：在二级页面提供“原图叠加层”，显示已识别的轴、图例、数据点；支持用户拖拽修正轴参考点、删除错误点、补充单位/标签；所有修改写入 logs 与版本化结果（可回滚）。

### 隐私与合规性要点

在中国法域语境下，图片及其元数据若包含可识别自然人的信息，可能构成个人信息；处理应遵循合法、正当、必要、最小范围、公开透明等原则，并明确目的与范围。citeturn9search1 数据与分析产物（尤其是日志、引用片段、检索记录）必须坚持“最小化留存”，并为敏感字段提供脱敏/裁剪策略；数据安全保护义务也应结合《数据安全法》的一般要求建立分类分级、访问控制与安全措施（适用范围与落地细则：**未指定**）。citeturn9search2

图像保留策略（是否长期保存原图、是否允许导出带标注的副本、presigned URL 有效期与权限）与日志保留策略（保留多久、是否可被用户删除、是否进入审计系统）均为**未指定**，但建议默认“能用即删/短期保留+可配置”，并确保外部检索（groksearch/Dify）不泄露用户私密图像内容（例如只传递必要的关键词与抽象描述，而非整图或完整 OCR 原文；除非用户明确授权）。

## 可扩展性、运维建议、风险与替代方案

### 性能估算与架构建议

由于时延与并发目标**未指定**，建议用“分阶段计时”建立基线：预处理+OCR、图表识别与数据提取、重建校验、检索、融合生成分别记录 `duration_ms`，并在 WebSocket 事件与 logs 中可观测。前端已具备基于 WebSocket 的任务状态展示与重连退避机制，适合承载长任务反馈。fileciteturn49file0L1-L1

异步任务队列：仓库文档已推荐“业务后端/工作流引擎 + 执行层（Claude Code/Vision/Python worker）”分层，以及在需要时引入 Celery/Temporal 等长流程编排。fileciteturn34file0L1-L1 因逐图解析属于典型长任务，建议：

- 同步接口只“创建分析任务”并返回句柄；
- worker 异步执行逐图解析与检索融合；
- 结果回写 `analysis_runs.result_payload_json`；
- WebSocket 推送进度（聚合或逐图）。

缓存策略：对同一张图的 OCR 与组件检测结果可缓存（以图片 hash/asset version 为键），避免重复；对检索结果可按 query+时间窗缓存（但需注意引用的“新鲜度/可复查性”）。

监控指标：任务成功率、平均耗时、P95 耗时、needs_review 占比、引用生成失败率、Dify 检索命中率、groksearch 超时率、写作模块消费失败率（schema 校验失败）等。

告警建议：连续失败、外部检索不可用、队列积压、单图耗时异常、needs_review 激增、引用缺 DOI/URL 的比例超阈值。

### 主要风险点与缓解措施

数据提取可靠性风险：复杂图（双轴、多子图、背景网格、低分辨率）会导致自动提取失败。缓解：采用“可降级输出 + 人工校准”并提供交互纠偏；对低置信结果不进入写作可用池。citeturn0search1turn2search1

引用与证据错配风险：模型可能生成“看似合理但无证据”的描述。缓解：强制 evidence_map 机制：每个关键陈述必须绑定 citation 与片段；无直接文献时采用回退策略（见下条），并明确标注“缺乏直接证据”。

无直接文献时的回退策略：当 groksearch/Dify 均无法提供直接支撑时，只输出“图像事实层”（数据表、趋势描述、轴单位等），并把“解释性/机制性叙述”降级为“假设/待证实”，不进入 Evidence Matrix 的可批准结论；必要时提示用户补充关键背景（实验方法、样本信息、原始数据表）。这一策略与仓库强调的“写作必须受 Claim–Evidence Matrix 约束”一致。fileciteturn34file0L1-L1

外部工具与接口变动风险：Claude Code CLI 版本与输出格式可能演进；建议遵循其官方 CLI/Headless 文档并对输出做稳健解析（stream-json）。citeturn6search0turn6search2 Dify API 也应以其 API Reference 为准，且 API Key 仅保存在服务端。citeturn13view0

### 关键参考来源

本设计关键参考的高质量来源包括：ChartOCR（统一图表数据提取的深度+规则混合框架）citeturn0search0、DePlot（plot-to-table 转换并与 LLM 推理结合）citeturn3view0、ChartSense（交互式图表数据提取系统）citeturn0search1、WebPlotDigitizer（半自动数据提取工具与引用方式）citeturn2search1、PlotQA/ChartQA（图表理解与问答基准数据集，为评测与能力边界提供参照）citeturn4view0turn3view1、PaddleOCR（面向多语言 OCR/结构化解析的开源能力与文档）citeturn0search4turn0search5、Claude Code CLI/Headless/MCP 官方文档（工具接入与流式输出）citeturn6search0turn6search2turn7search0、Dify 知识库索引与检索 API（/datasets/{dataset_id}/retrieve）citeturn13view0turn5search1、以及 WCAG/WAI-ARIA 相关可访问性标准建议。citeturn8search6turn8search5
