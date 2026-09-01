# Project knowledge discovery

Use this reference after classifying the surface. The goal is a sufficient evidence map, not exhaustive reading of the repository.

## Source roles

Treat sources according to what they can establish:

1. The user's current statements establish desired direction and authorization, but factual claims may still need project evidence.
2. Product requirements, research, domain notes and decision records establish intended behavior and business meaning.
3. Code, configuration, schemas, tests and rendered behavior establish implemented behavior.
4. Existing interface copy establishes what users currently see, not whether it is true or strategically correct.
5. External sources establish current market, regulatory or industry facts only when the task authorizes or requires external research.

When intended and implemented behavior differ, record a conflict instead of silently choosing one. A content change cannot repair the product behavior; surface that product issue separately.

## Common repository search

Start at the target route or component and expand outward. Use `rg --files` and `rg` for likely sources such as:

- `README`, `ABOUT`, `CONTEXT`, `AGENTS`, product briefs, specs, ADRs and research folders
- routes, navigation, page titles, metadata and adjacent components
- localization resources, validation messages, empty states, notifications and accessibility labels
- schemas, API contracts, permission checks, feature flags, tests and fixtures that reveal actual behavior
- glossary, domain model, demo scripts, sales material and user/persona research

Record why a consulted source matters. For global audits, record meaningful exclusions so coverage is reviewable.

If `.userese/project-profile.json` exists, use it as a cache of previously confirmed knowledge, not as unquestionable truth. Recheck claims affected by code, product or audience changes. Persist only user-confirmed facts that are likely to matter again, with their evidence and confirmation date; keep one-off page choices inside the run. If only a legacy `.uxplain/` or `.frontend-content-design/` location exists, read it for compatibility and write new or updated artifacts under `.userese/`.

## Surface-specific discovery

### Personal or portfolio homepage

Look for resumes, project histories, case studies, essays, biographies and stated opportunity preferences. The repository can prove work and patterns; it usually cannot decide the identity the person wants to project. Ask about desired opportunities, memorable qualities and unwanted interpretations when those are absent.

### Product or marketing homepage

Find the product's job, primary user, triggering situation, alternatives, proof, objections and conversion goal. Separate product capability from aspiration. Claims about outcomes, speed, scale, price or trust require evidence.

### Operational interface

Trace the user action through handlers, state, permissions, validation and recovery paths. Copy must describe the actual result and consequence. A vague or misleading workflow may require a product-design finding rather than a rewrite.

### Professional or decision-support interface

Identify the working role, decision being made, time horizon, data provenance, uncertainty, domain vocabulary and cost of misunderstanding. Preserve useful expert terms and explain only what the selected audience does not reliably know. Do not turn estimates, forecasts or partial data into certainty.

## Knowledge statuses

For each high-impact finding record:

- `id`
- `statement`
- `status`: `verified`, `inferred`, `conflict`, or `unknown`
- `sources`: exact paths, symbols, lines or user confirmation
- `impact`: what would change if the statement is wrong
- `next_step`: use, label assumption, ask, or block

Evidence is sufficient when every message the page relies on is either verified, explicitly confirmed by the user, or presented with uncertainty matching its evidence.

## Question gate

Ask only when the answer is absent and materially changes one of these:

- primary audience or their situation
- page job or desired next action
- personal/product positioning
- factual claim, consequence or risk
- message hierarchy or a non-negotiable exclusion

Ask a compact batch of at most three questions after repository discovery. Prefer a proposed understanding the user can correct over an empty question. Example:

> I currently understand the page as serving coal-trade managers who need a risk overview before a weekly decision. The repository also mentions analysts. Which role should the first screen optimize for?

Voice adjectives, minor wording preferences and reversible layout-level choices normally become labeled assumptions instead of interruptions.
