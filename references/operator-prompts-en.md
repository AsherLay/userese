# English operator prompts

Use this file when the user is working in English. It is the English counterpart of the Chinese stop-and-ask lines in `SKILL.md`. Keep the same gates, IDs, and approval boundaries. Do not invent extra checkpoints.

`Surface.locale` is the language of the page. Talk to the user in the language they are using.

Rendered files such as `scan-plan.md` still use Chinese headings. When showing them to an English-speaking user, restate the meaning in English. Do not paste Chinese labels as if they were the UI.

## Start

```text
Use $userese to find the user-facing language in this project. First confirm who I want to read it, then propose a full rewrite from that reader's point of view. Do not edit source files yet.
```

If the user already named a route, role, reader, or locale, keep those and only ask for the missing low-risk fields.

## Reader

If the user has not said who the copy is for, ask before detailed writing:

```text
Who should this be written for? A first-time visitor, someone in the middle of a task, or a specialist making a decision?

I'll use that as the reader for the rewrite. Correct me if this is wrong.
```

## Surface

Propose a surface the user can correct:

```text
Target surface (please correct if this is wrong):
- Route / entry:
- User role:
- Page language:
- Device / viewport:
- Default state:
- Extra states you want covered:

I'll treat missing low-risk fields as temporary assumptions. If a state needs credentials or extra permission, I'll skip collecting it and record the limit.
```

## Mode

After the scan card, stop here:

```text
Scan card is ready. I have not written a Writer brief, and I have not edited product files.

Relative effort:
- core (default): the copy that carries understanding, judgment, or action
- surface: all product expression on this surface
- project: selected surfaces and channels

Which depth do you want?
```

Do not start detailed semantic analysis without a mode.

## Inventory

After the detailed list:

```text
Here is the copy list for the current mode. This is coverage and scope, not a rewrite.

You can include all detailed items, a page/section, a category, or specific copy-* IDs.
Items left in grouped coverage were found but not reviewed. That is not the same as you excluding them.
```

Every detailed item must become `include` or `exclude` after this answer.

## Limited interview

Ask at most three deciding questions, once, after reading the project:

```text
I still need these before I can set audience, page job, or claims without misleading anyone:
1.
2.
3.

If you'd rather not answer now, I can ship what is known plus the open gaps.
```

## Direction

For core narrative or a real positioning change:

```text
Diagnosis is in diagnosis.md. Direction options are in strategy.md.

Which direction do you want, or what should I change?
```

For task UI and low-risk microcopy, skip this stop when facts, behavior, and audience are already clear. Write the assumptions into the brief and continue.

## Writing pipeline

```text
Writing setup (please confirm; defaults are only preselected):

- Discovered:
- Analyzed in this mode:
- Grouped only:
- You selected:
- Going to the Writer:
- Blocked by knowledge gaps:

Writer: host agent (default, no extra model call), or type the exact Writer skill name.
De-AI pass: none (default), or type the exact skill name.

I will not scan installed skills or pick one for you.
```

Do not generate copy until this is answered.

## Delivery

```text
Source files were not modified.

Copy proposals are in before-after.md. Non-copy suggestions, if any, are listed separately.

Please choose independently:
- approve all copy, or approve specific copy-* IDs
- approve specific suggestion IDs
- ask for a revision
- discard

Approving copy does not approve layout, product, or visual changes.
```

If a critical state was inaccessible, do not say the job is complete.

## Workspace and production

After copy approval:

```text
I'll edit only the approved copy-* IDs at their exact locations. I still will not commit, push, merge, deploy, or publish unless you ask after seeing the actual diff.
```
