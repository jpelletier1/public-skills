# Templates

## GitHub issue body (draft content)

Write the anonymized content to `/tmp/linear-github-sync/<LINEAR-ID>.md`. Keep the
structure of the Linear description when it has one. When it has none, use:

```markdown
## Summary

<One or two sentences: the problem and who it affects, anonymized.>

## Details

<What the customer is trying to do, what happens, and what they expect.>

## Example scenario

<A concrete, anonymized scenario. AlphaCo's admin tries to ... and ...>

## Acceptance criteria

- [ ] <Only if the Linear ticket states them.>
```

Do not add the sync-history block. `feedback_sync.py` appends it:

```markdown
---
<!-- linear-feedback-sync -->
#### Sync history
_Synced from Linear by an AI agent (OpenHands)._

- v1 · 2026-11-01 · Created from Linear PRD-123
- v2 · 2026-11-06 · Updated from Linear PRD-123
```

On update, the script keeps the existing history lines and appends the next
version. A GitHub issue with no history block gets `v1 · ... · Updated`.

## Labels for a new issue

- `bug`: the ticket reports broken or regressed behavior.
- `enhancement`: everything else (feature requests, improvements, feedback).

No assignee.

## Linear approval comment

Post with `save_comment` (Linear MCP). Only the mention, the link, and the AI note.
Do not include the draft, the alias mapping, or any GitHub text.

```markdown
@<displayName> A GitHub sync draft for this ticket is ready for your approval: <CONVERSATION_URL>

_Posted by an AI agent (OpenHands) on behalf of <name>._
```

## Linear completion comment

After the GitHub write succeeds, the Linear ticket links to the issue, and the label
is removed:

```markdown
Synced to OpenHands/enterprise#<N> (v<VERSION>): <GITHUB_ISSUE_URL>

_Posted by an AI agent (OpenHands) on behalf of <name>._
```

## Draft presentation in the conversation

For each ticket, show the user:

````markdown
### PRD-123 → <new issue | OpenHands/enterprise#456 (v2)>

**Aliases:** Acme Corp → AlphaCo · Jane Doe (Acme) → "a customer platform engineer"

<dry-run output, verbatim, in a fenced block>

Reply "approve PRD-123", or tell me what to change.
````
