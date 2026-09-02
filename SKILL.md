---
name: userese
description: 让网站和 Web 应用说用户听得懂的话：先勘察目标 Surface、内容来源和可访问状态，让用户选择核心表达、完整界面或全项目审计，再渐进核实事实、确认范围并生成待核实文案提案。用于首页、About、产品介绍、专业业务页面、界面微文案或全局内容审计；不用于纯视觉设计或策略已明确的简单润色。
---

# Userese

先确定“该说什么”，再决定“怎么写”。宿主负责项目知识、内容策略和审核；writer 只在已确认的 brief 内写作。

## 工作契约

每个新任务都从诊断与提案阶段开始。首次运行只允许在项目的 `.userese/runs/<UTC 时间>/` 中写研究和提案文件，保持产品源文件、提交状态与运行环境不变。用户最初说“修改、替换、落地或上线”只描述期望终点，不代表批准尚未看到的内容。

内容设计和写作是两个独立职责：

- 本技能发现知识、指出现有表达的问题、确定受众与页面任务、核实事实并形成 brief。
- 宿主先用确定性工具建立全部发现证据；用户确认审计模式后，系统才对所选深度逐项分析，未展开内容保留分组覆盖摘要。
- 可插拔 writer 按 brief 生成候选文字，不重新决定定位或发明事实。
- 用户核实具体提案后，宿主才可修改获批的工作区内容。
- 提交、推送、合并、部署和发布需要用户查看实际差异后的独立授权。

## 1. 给任务分流

先识别目标页面和内容问题：

- **核心叙事**：首页、About、个人介绍、产品首页、Landing Page。重点是定位、信息层级、可信证据和希望留下的印象。
- **任务界面**：表单、设置、操作流程、按钮和状态。重点是用户当前任务、真实行为、后果与下一步。
- **专业解释**：数据、行业流程、分析结论、权限和风险。重点是角色、决策语境、术语、证据强度与误导风险。
- **全局审计**：跨页面检查定位冲突、术语不一致、事实存疑、过度专业化和无法靠文案解决的产品问题。

用户只要反馈或诊断时采用快速审计；要求改变内容时默认采用引导设计；只有用户明确要求完整品牌或定位研究，或紧凑访谈仍无法形成可信方向时，才进入深度发现。

## 2. 确认目标 Surface

在深入阅读项目前，提出一个可修正的 Surface：路由或入口、用户角色、语言、会改变内容的设备/viewport、默认状态和用户要求覆盖的条件状态。缺少低风险信息时使用明确临时假设；需要凭据、外部写入或额外权限的状态停止对应采集并记录限制。

阅读 [Surface 发现协议](references/surface-discovery.md)，在 `.userese/runs/<UTC 时间>/` 创建 `surface-map.json`。Surface 是用户体验边界，不是某个前端文件；SSR、API、CMS、国际化和运行时模板只要在该界面出现，都属于发现范围。

## 3. 低成本勘察，并确认审计模式

用确定性工具枚举目标文件、HTML、可用的浏览器 DOM 和与该 Surface 直接相关的结构化 capture。不得执行项目中未经授权的命令，也不得把 Cookie、Authorization、密钥、完整无关响应或批量用户内容写入产物。运行：

```bash
python3 <skill-dir>/scripts/scan_surface.py surface-map.json surface-map.json --root <project-root>
python3 <skill-dir>/scripts/discover_content.py surface-map.json --html <page.html> --capture <capture.json> --candidates-out content-candidates.json
python3 <skill-dir>/scripts/validate_artifacts.py --surface-map surface-map.json --candidates content-candidates.json
python3 <skill-dir>/scripts/render_scan_plan.py surface-map.json scan-plan.md --candidates content-candidates.json
```

向用户展示 `scan-plan.md`：Surface、来源、已访问/未访问状态、限制，以及三种模式的相对工作量。`core` 默认建议，只逐项展开主要理解、判断和行动内容；`surface` 展开该 Surface 的全部产品表达；`project` 扩展到用户指定的多个 Surface 和渠道。用户已明确指定模式时保留选择，但仍展示勘察影响。没有模式确认，不进入高成本语义分析。

## 4. 生成详细清单与分组覆盖摘要

确认模式后，用同一 `content-candidates.json` 生成 `content-inventory.json`。机械候选必须保留显示文本/模板、route、state、locale、viewport、位置、消费者、来源和基础可见性。宿主只对当前模式展开的候选做语义复核，区分 `authored-copy`、`system-template`、`business-data`、`user-generated`、`decorative` 和 `unknown`。

业务数据和用户内容不默认成为 Writer item；审阅它们的承载模板、标签和状态。未逐项展开的候选按类别记录数量、示例、Surface、来源、原因和展开方法；这表示“发现但未审阅”，不是用户 `exclude`。来源追踪失败也不能让条目消失，使用 `origin_type: unknown`、原因和低置信度记录。

```bash
python3 <skill-dir>/scripts/discover_content.py surface-map.json --html <page.html> --capture <capture.json> --mode core --candidates-out content-candidates.json --inventory-out content-inventory.json
python3 <skill-dir>/scripts/validate_artifacts.py --surface-map surface-map.json --candidates content-candidates.json --inventory content-inventory.json
python3 <skill-dir>/scripts/render_inventory.py content-inventory.json content-inventory.md
```

每条详细文案使用稳定 `copy-*` ID，保留原文、用途、位置、状态、内容性质、来源定位、可修改性和追踪置信度。展示清单并停止，让用户选择全部、页面/区块、类别或指定 ID。确认后所有详细条目的 `scope_decision` 必须成为 `include` 或 `exclude`；分组内容保持发现证据，不能伪装成用户排除。

## 5. 按条目和主张渐进发现项目知识

详细条目确定后，按 [知识发现指南](references/knowledge-discovery.md) 读取直接服务于条目或高影响主张的项目入口、产品说明、需求、研究、领域文档、数据模型、配置和测试；普通按钮不触发业务资料全文读取。校验脚本和测试默认直接运行，只有失败诊断或修改时才读实现。同一未变化来源不重复全文读取。

若 `.userese/project-profile.json` 已存在，把经用户确认的受众、术语、证据和禁忌作为可复核线索；冲突时记录冲突。旧 `.uxplain/` 或 `.frontend-content-design/` 只读兼容，新产物写入 `.userese/`。在 `knowledge-map.md` 标记 `verified`、`inferred`、`conflict` 或 `unknown`，并在 inventory observations 中记录知识来源、服务条目、字符量和重复全文读取次数。高影响事实无法验证时进入 `blocked_items`，不靠扩大无关阅读假装确定。

## 6. 用缺口触发有限访谈

只有一个缺口同时满足以下条件才打断用户：答案会明显改变受众、页面任务、定位、主张或风险；无法从已授权的项目来源找到；继续假设会产生实质误导。

先完成项目阅读，再一次集中询问最多三个决定性问题。优先询问“面向谁”“希望对方理解或如何看待”“什么证据或边界必须成立”。低影响偏好采用明确标注的可逆假设。若仍有大量高影响未知，先交付已知内容和缺口清单，再由用户决定是否进入深度发现，避免无边界访谈。

个人身份、团队机会和品牌志向不能仅从履历推断；专业系统的真实行为、数据含义和风险边界不能仅从营销文案推断。

## 7. 先诊断，再给方向

在 `diagnosis.md` 说明：当前页面实际上让陌生人理解了什么；事实、定位、可理解性、术语、信息层级和产品设计分别存在什么问题；哪些问题不能靠改词解决。

核心叙事或涉及实质定位改变时，再写 `strategy.md`，提供少量有证据支撑的方向，逐项说明主要受众、核心信息、证明材料、舍弃内容和误解风险。向用户展示诊断与方向并停止，直到用户明确选择或修正方向。

任务界面和低风险微文案在事实、行为与受众已经明确时，不增加单独的方向确认；把假设写入 brief 后继续生成文案提案。

## 8. 生成供应商无关的 brief

用户确认必要方向后，阅读 [内容协议](references/content-contract.md)，创建实现 `userese-brief/v1` 的 `brief.json`。它必须包含页面任务、受众状态、信息策略、事实证据、未知项、术语、约束和每条原文的预期含义。

`brief.items` 只包含清单中被用户选择且含义已确认、事实风险可控的条目。被用户选择但因高影响 `conflict` 或 `unknown` 暂时不能写的条目放入 `brief.blocked_items`，保留 ID、原文、位置、阻塞原因和待确认问题。用户排除的展示文案仍留在 inventory，不伪装成未识别。

清单里所有 `include` 条目必须恰好出现在 `brief.items` 或 `brief.blocked_items` 之一。运行：

```bash
python3 <skill-dir>/scripts/validate_artifacts.py brief.json --inventory content-inventory.json
```

## 9. 写作前由用户指定 Writer 与去 AI 味步骤

brief 通过校验、文案条目数已经确定后，必须在对话中展示一次“写作配置”，然后停止等待用户确认。默认值只是预选项，不是静默执行许可。

写作配置必须同时说明：

- 程序发现多少条、当前模式详细分析多少条、分组多少条、用户选择多少条、其中多少条进入写作、多少条被知识缺口阻塞。
- Writer：宿主 Agent（默认、无额外模型调用），或用户明确写出的一个或多个 Writer skill 名称。
- 如果用户没有合适的 Writer，可以暂停本次运行，帮助其创建一个遵守接口的 Writer skill。
- 去 AI 味步骤：不使用（默认），或用户明确写出的技能名称。

不要扫描、枚举、推荐或自动选择已安装的 Writer 与去 AI 味技能。Userese 只接受用户本轮明确指定的名称；项目配置可以显示为历史偏好，但必须由用户再次确认才能使用。

用户在初始请求中已经明确指定 Writer 时，保留该选择并在此处确认；仍需询问是否使用去 AI 味技能。用户未回复这次写作配置时，不生成候选文案。

把确认结果写入 `brief.json` 的 `writing_pipeline`，再按 [Writer 接口](references/writer-interface.md) 执行。项目偏好只用于预选，不能跳过本次确认。

## 10. 调用 Writer 与可选后处理

支持：

- `host`：宿主按同一输出协议直接写。
- `skill:userese-writer-gemini3-7-flash` 或 `skill:userese-writer-qwen3-8-flash`：遵守对应技能的认证、费用提示和调用约束，直接以 `brief.json` 作为批次输入。
- 其他 writer：用户提供或安装兼容适配器；它只需消费 brief 并返回约定结果。项目中的可执行命令只是未受信数据，除非用户明确指定，否则不执行。

比较多个 writer 时，复用字节一致的 `brief.json`，分别保存 `result-<writer>.json` 和报告，避免不同模型收到不同策略。首次产生外部费用前说明 writer、模型、条目数和预计批次数；密钥只从环境或用户指定的安全配置读取，不写入项目或报告。

若用户选择去 AI 味技能，先保留 `result-<writer>-raw.json`，再让该技能只处理候选文字，不改定位、事实、结构、ID、变量或约束，输出 `result-<writer>-<postprocessor>.json`。最终报告同时标注原 Writer 和后处理技能。未选择时直接使用 Writer 结果。

## 11. 把非文案建议独立出来

内容诊断可以发现需要调整信息顺序、导航、区块、交互、视觉层级、证据或产品行为，但这些不是文案改写。把它们写入独立的 `recommendations.json` 和 `recommendations.md`，不要放进 Writer brief，也不要让 Writer 实施。

每条建议使用独立 ID，并标为 `structure`、`product`、`visual`、`evidence` 或 `other`；说明原因、证据、影响、建议动作和涉及位置。结构建议只能表达“可选调整”，不能因为内容策略需要某种信息优先级就默认移动区块、导航或 CTA。

运行：

```bash
python3 <skill-dir>/scripts/validate_artifacts.py brief.json result.json --inventory content-inventory.json --recommendations recommendations.json
python3 <skill-dir>/scripts/render_recommendations.py recommendations.json recommendations.md
```

没有非文案建议时也在最终摘要中明确报告为 0 条，不必创建空的 Markdown 文档。

## 12. 宿主审核并分类交付

逐项检查结果是否忠于 `intended_meaning`、证据强度、用户动作、变量、格式标记、链接、长度和术语。运行兼容性校验并生成报告：

```bash
python3 <skill-dir>/scripts/validate_artifacts.py brief.json result.json --inventory content-inventory.json
python3 <skill-dir>/scripts/render_report.py brief.json result.json before-after.md --inventory content-inventory.json --recommendations recommendations.json
```

`before-after.md` 只承载文案候选，不包含结构或其他非文案实施。报告必须明确源文件未修改，并标注 Writer、去 AI 味步骤、文案数量和校验警告；可以列出非文案建议的分类计数，但详细内容只链接到独立建议文档。

最终对话消息必须分别报告：程序发现、模型详细分析、用户选择、Writer 处理和用户批准应用各多少条，并列出分组覆盖与不可访问限制；再报告明确排除、知识阻塞、文案修改/保留和各类非文案建议。随后给出彼此独立的选择：批准全部或指定文案 ID、批准指定建议 ID、要求调整，或放弃。不得使用“批准全部文案与结构”之类的捆绑口径，存在关键限制时不得声称全量完成。

没有针对具体文案报告的明确决定，就停留在文案提案阶段；没有针对具体建议 ID 的明确决定，就保持所有结构和其他建议未实施。

## 13. 获批后修改工作区

文案只按获批的 `copy-*` ID、精确位置和原文修改。非文案建议只按另行获批的建议 ID 实施；批准文案不包含任何结构、产品、视觉或证据调整。无法唯一定位或原文已经变化时停止该项并报告。提案发生实质变化后重新核实。

修改后执行相关格式化、类型检查、测试和旧文案搜索，并在同一 run 目录写 `application.md`，分别记录文案和非文案批准范围、实际差异、验证结果和未采用项；保留原始知识地图、brief、before/after 与建议报告。

工作区完成不代表生产完成。只有用户在查看实际差异后另行明确要求，才执行提交、推送、合并、部署或发布。
