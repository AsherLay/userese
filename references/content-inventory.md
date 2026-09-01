# User-facing content inventory

Use this contract before diagnosis or writing whenever the user asks to change content. The inventory is the coverage record; `brief.json` is only the selected, write-ready subset.

## Coverage boundary

Inspect the requested routes in source and, when runnable, in the rendered interface. Inventory every string a user can encounter in that boundary:

- navigation, headings, paragraphs, lists, case narratives, CTAs and links
- labels, help text, placeholders, validation, errors, empty/loading/success states and confirmations
- captions, alt text, accessibility labels, page titles, descriptions and social-preview copy
- text assembled from content files, localization resources, component data or runtime responses

Developer logs, tests, code identifiers and server-only messages are not inventory items. Record the source patterns checked and meaningful exclusions under `coverage`; put uncertain visibility in the inventory with `visibility: "unknown"`. Embedded text in images, unreachable states and remote content belong in `coverage.limitations` when they cannot be inspected.

Repeated strings with different jobs or locations are separate items. A shared source rendered in several equivalent locations may be one item only when all consumers and contexts are recorded.

## JSON contract

Store the source of truth as `content-inventory.json`:

```json
{
  "surface": {
    "name": "Homepage",
    "routes": ["/"],
    "paths": ["index.html"]
  },
  "coverage": {
    "source_files": ["index.html"],
    "rendered_routes": ["/"],
    "states_checked": ["default"],
    "excluded_source_patterns": [
      {"pattern": "tests/**", "reason": "not shipped to users"}
    ],
    "limitations": ["The contact form error state was not runnable"]
  },
  "selection": {
    "status": "pending",
    "confirmed_at": null,
    "note": ""
  },
  "items": [
    {
      "id": "copy-001",
      "location": {
        "path": "index.html",
        "line": 120,
        "symbol": "CaseStudyDelivery"
      },
      "route": "/",
      "section": "案例 / 外卖调度",
      "kind": "body",
      "original": "2015 年外卖订单涨得太猛……",
      "purpose": "解释问题规模和人工调度瓶颈",
      "visibility": "default",
      "proposed_treatment": "keep",
      "proposal_reason": "过程具体且陌生人能够理解；仍应由用户决定是否纳入审阅。",
      "scope_decision": "pending"
    }
  ]
}
```

Required top-level objects are `surface`, `coverage`, `selection`, and a non-empty `items` array. Every item requires `id`, `location`, `route`, `section`, `kind`, `original`, `purpose`, `visibility`, `proposed_treatment`, `proposal_reason`, and `scope_decision`.

- `id` uses a stable `copy-*` value and is reused by the brief and writer result.
- `visibility` is `default`, `conditional`, `dynamic`, `metadata`, `accessibility`, or `unknown`.
- `proposed_treatment` is the host's recommendation: `review`, `keep`, or `needs-context`.
- `scope_decision` is `pending`, `include`, or `exclude`. It records the user's scope choice, not the host's quality judgment.

## Scope checkpoint

Render `content-inventory.md`, tell the user what was and was not covered, and let them select all copy, named pages or sections, or individual IDs. A target such as “homepage” identifies where to scan; it does not decide which recognized items may disappear from review.

Before the user chooses, keep `selection.status` and all item decisions `pending`. After the user chooses:

- set `selection.status` to `confirmed`;
- record the current-conversation confirmation in `selection.note` and `confirmed_at`;
- resolve every item to `include` or `exclude`.

The host may propose a convenient selection, but only the user's response confirms it. When the user selects a whole page or section, resolve all matching IDs explicitly so later validation can prove coverage.

## Handoff invariant

Every `include` ID appears exactly once in either `brief.items` or `brief.blocked_items`. `brief.items` goes to the Writer. `brief.blocked_items` preserves selected copy that cannot yet be written safely, with its original text, location, reason and deciding question. Every `exclude` ID remains visible in the inventory and stays out of both arrays.

This invariant distinguishes four outcomes that must never be conflated: not discovered, discovered and excluded by the user, selected and ready to write, or selected but blocked by missing knowledge.
