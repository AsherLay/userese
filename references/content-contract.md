# Content brief contract

`brief.json` is the durable handoff between content strategy and any writer. It is UTF-8 JSON and deliberately extends the batch format used by `writer-gemini` and `write-qwen`, so those scripts can consume it without conversion.

```json
{
  "run": {
    "project": "Example product",
    "goal": "让目标用户理解页面价值并采取下一步",
    "target_language": "zh-CN",
    "profile_source": "README, product spec and user confirmation",
    "surface": {
      "name": "Homepage hero",
      "kind": "core-narrative",
      "paths": ["src/app/page.tsx"]
    },
    "page_job": "让第一次访问者在十秒内理解产品服务谁、解决什么问题",
    "audience": "第一次了解该产品的煤炭贸易业务负责人",
    "audience_detail": {
      "situation": "准备判断近期采购与库存风险",
      "knowledge": ["熟悉煤炭贸易", "不了解预测模型实现"],
      "needs": ["先看到业务结论", "能继续检查依据"]
    },
    "communication_goal": "先说明决策价值，再解释方法",
    "brand_voice": ["清楚", "克制", "可信"],
    "avoid": ["把概率写成确定结论", "使用没有解释的模型术语"],
    "terms": [
      {"concept": "forecast interval", "preferred": "预测区间", "avoid": ["准确价格"]}
    ],
    "message_strategy": {
      "desired_understanding": ["这是辅助判断风险的工具"],
      "desired_perception": ["懂业务边界", "结论可以追溯"],
      "next_action": "查看本周风险摘要",
      "message_hierarchy": ["业务结论", "主要依据", "不确定性", "详细分析"]
    },
    "knowledge": {
      "verified_claims": [
        {"id": "claim-001", "statement": "输出包含预测区间", "evidence": ["forecasting/output.py:80"]}
      ],
      "assumptions": [],
      "conflicts": [],
      "unresolved": []
    },
    "global_constraints": ["不新增能力、保证、价格或时效"]
  },
  "writing_pipeline": {
    "writer": {
      "type": "host",
      "name": "host-agent",
      "model": "current-host-model"
    },
    "postprocessors": [],
    "selection_note": "User confirmed host writer and no postprocessor."
  },
  "items": [
    {
      "id": "copy-001",
      "location": {
        "path": "src/app/page.tsx",
        "line": 42,
        "symbol": "Hero"
      },
      "purpose": "首屏标题，建立页面的核心价值",
      "original": "AI-powered coal intelligence",
      "context": "下方是风险摘要入口",
      "intended_meaning": "系统帮助业务负责人理解近期风险，不替代其决策",
      "evidence_refs": ["claim-001"],
      "constraints": ["不承诺预测准确率", "不超过 22 个汉字"]
    }
  ],
  "blocked_items": [
    {
      "id": "copy-002",
      "location": {"path": "src/app/page.tsx", "line": 68},
      "original": "每天节省 80% 调度时间",
      "reason": "项目内没有找到该比例的来源",
      "question": "是否有可核实的数据来源，还是删除这个数字？"
    }
  ],
  "excluded": [
    {"location": "src/server/log.ts", "reason": "仅开发日志，不面向用户"}
  ]
}
```

## Required fields

The `run` object requires all of these fields:

- compatibility fields: `project`, `goal`, `target_language`, `audience`, `brand_voice`, `terms`, `global_constraints`
- content-design fields: `profile_source`, `surface`, `page_job`, `audience_detail`, `communication_goal`, `avoid`, `message_strategy`, `knowledge`

Each item requires `id`, `location`, `purpose`, `original`, `context`, `intended_meaning`, `evidence_refs`, and `constraints`. Keep `original` byte-for-byte identical to source. Record variables, markup, URLs, keyboard shortcuts and hard length limits in `constraints`.

`blocked_items` is required and may be empty. It contains copy selected by the user but withheld from the Writer because a high-impact fact, meaning or behavior is unresolved. Each blocked item keeps its inventory `id`, `location`, byte-identical `original`, a non-empty `reason`, and the `question` whose answer would unblock it.

The top-level `writing_pipeline` is required before writing begins. It contains one confirmed `writer`, a `postprocessors` array, and a non-empty `selection_note`. An empty postprocessor array means the user chose no de-AI pass. A project default may prefill these values, but the note must reflect the current conversation's confirmation.

`surface.kind` is one of `core-narrative`, `task-interface`, `professional-explanation`, or `global-audit`.

`knowledge.verified_claims` must use unique IDs. Every `evidence_refs` value must point to one of those IDs. If an intended meaning depends on unresolved or conflicting knowledge, put it in `blocked_items` until it is confirmed. Do not reinterpret “blocked” as user exclusion. When `content-inventory.json` is supplied to validation, its `include` IDs must equal `items` plus `blocked_items`; read [content-inventory.md](content-inventory.md) for the coverage contract.

## Proposal result

Every writer returns the same minimum structure:

```json
{
  "pipeline": {
    "writer": {
      "type": "host",
      "name": "host-agent",
      "model": "current-host-model"
    },
    "postprocessors": []
  },
  "items": [
    {
      "id": "copy-001",
      "decision": "rewrite",
      "rewrite": "先看清风险，再决定下一步",
      "rationale": "先呈现业务任务，并避免承诺确定预测。"
    }
  ],
  "validation": {
    "errors": [],
    "warnings": []
  }
}
```

`decision` is `rewrite`, `keep`, or `needs-context`. Return exactly one result for every input ID. With `keep` or `needs-context`, preserve the original unless the adapter has a documented reason not to. Provider-specific metadata such as model, token usage, reasoning level and batch count may be added.

## Non-copy recommendations

Keep structure, product, visual, evidence and other non-copy suggestions outside `brief.json`. Store them in `recommendations.json`:

```json
{
  "items": [
    {
      "id": "structure-001",
      "type": "structure",
      "title": "把当前 AI 项目提前到历史案例之前",
      "reason": "当前顺序让过去经历压住已确认的 AI Builder 定位",
      "evidence": ["strategy.md: direction A", "index.html:#projects"],
      "impact": "首次访问者会更早看到当前身份的证明",
      "proposal": "调整两个现有区块的顺序，不改变区块内部文案",
      "locations": ["index.html:#projects", "index.html:#experience"]
    }
  ]
}
```

`type` is one of `structure`, `product`, `visual`, `evidence`, or `other`. IDs use the type as their prefix. These recommendations are optional and require approval independent from all `copy-*` items. Render their details into `recommendations.md`; the copy report and final chat may show only category counts and a link.

## Persistent project profile

`.userese/project-profile.json` is an optional cache for knowledge the user has confirmed and future runs will reuse. Keep it smaller than a run brief:

```json
{
  "confirmed_at": "2026-09-01T00:00:00Z",
  "audiences": [],
  "positioning": [],
  "verified_claims": [],
  "terms": [],
  "voice": [],
  "avoid": [],
  "open_questions": []
}
```

Every durable claim should retain its evidence or state that it came from explicit user confirmation. Do not copy transient page wording, API keys, or unrelated personal data into this profile. A profile reduces repeated questions; it does not override newer project evidence or the user's current direction.
