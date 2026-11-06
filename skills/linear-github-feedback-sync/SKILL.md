---
name: linear-github-feedback-sync
description: This skill should be used when the user asks to "sync feedback tickets to GitHub", "run the feedback GitHub sync", "sync Linear tickets labeled feedback-github-sync", "push Linear feedback to OpenHands/enterprise", "duplicate a Linear issue into the enterprise repo", or "/feedback-github-sync". Finds Linear issues in the OHE and PRD teams labeled feedback-github-sync, anonymizes customer names, drafts a new or updated OpenHands/enterprise GitHub issue with a versioned sync history, asks for approval through a Linear comment linking to the conversation, then writes to GitHub and removes the label.
---

# Linear → GitHub feedback sync

Copy the content of Linear tickets labeled `feedback-github-sync` (teams **OHE** and
**PRD**) into GitHub issues in **`OpenHands/enterprise`**, anonymized, after explicit
approval. Run on demand. Nothing is written to GitHub until the user approves the
exact text in this conversation.

`OpenHands/enterprise` is public. Anonymization is mandatory; follow
`references/anonymization.md` for every ticket.

## Tools and prerequisites

- **Linear MCP** for discovery, reading tickets, comments, labels, and links.
- **`scripts/feedback_sync.py`** (stdlib Python) for everything that must be exact:
  native-sync detection, the leak check, version numbering, and GitHub writes.
  Set `S=<this skill directory>/scripts/feedback_sync.py`.
- `GITHUB_TOKEN` with issue write access to `OpenHands/enterprise`.
- `LINEAR_API_KEY` for `links` (the MCP does not expose an attachment's
  `sourceType`). If it is missing, use the fallback in Step 2.

Work in `/tmp/feedback-sync/` and delete it at the end.

## Workflow

### Step 1: Find labeled tickets

Call `list_issues` twice, with `label: "feedback-github-sync"` and `team: "OHE"`,
then `team: "PRD"`. Follow `cursor` while `hasNextPage` is true. If nothing is
found, report that and stop.

Call `whoami` once. Its `displayName` is used for the @mention and `name` for the
AI note.

### Step 2: Classify each ticket

For each ticket, run:

```bash
python3 $S links <LINEAR-ID>
```

It lists the `OpenHands/enterprise` **issues** (not PRs) attached to the ticket.

| Result | Scenario |
|---|---|
| No enterprise issue | **Create**: draft a new issue |
| One enterprise issue, `natively_synced: false` | **Update**: draft a new body for that issue |
| Any enterprise issue with `natively_synced: true` | **Skip** (see below) |
| Two or more enterprise issues, none natively synced | Ask the user which one to update. Do not guess |

**Skip natively synced tickets.** Linear's own GitHub sync mirrors the description
both ways, so rewriting the GitHub body would overwrite the Linear description.
For these: do not draft, do not comment on Linear, leave the label on, and list
the ticket under "Skipped" in the final summary with the reason.

Fallback when `LINEAR_API_KEY` is not set: get attachments from `get_issue`, keep
URLs matching `github.com/OpenHands/enterprise/issues/<N>`, and treat a link as
natively synced if its attachment title has the form `#<N> <title>` **or** the
GitHub body matches the Linear description after whitespace normalization. When
unsure, skip and say why.

Mention links to issues in other repositories in the draft presentation, but do
not treat them as the target.

### Step 3: Draft the anonymized content

1. Read the full ticket with `get_issue` (title, description, labels, project,
   customer needs via `includeCustomerNeeds: true`). Read comments with
   `list_comments` only for context; do not copy them.
2. Call `list_customers` (all pages) to get the names to look for.
3. Write an anonymized title and body following `references/anonymization.md`.
   Body format is in `references/templates.md`. For **Update**, read the current
   GitHub body first and keep its structure and aliases where they still apply.
4. Save the body to `/tmp/feedback-sync/<LINEAR-ID>.md` and every replaced real
   term plus all customer names to `/tmp/feedback-sync/<LINEAR-ID>.deny`.
5. Render the exact final text:

   ```bash
   # Create
   python3 $S create --dry-run --linear-id PRD-123 --title "<anonymized title>" \
     --label enhancement --content-file /tmp/feedback-sync/PRD-123.md \
     --deny-terms /tmp/feedback-sync/PRD-123.deny

   # Update (add --title "<anonymized title>" only if the title should change)
   python3 $S update --dry-run --linear-id PRD-123 --issue 456 \
     --content-file /tmp/feedback-sync/PRD-123.md \
     --deny-terms /tmp/feedback-sync/PRD-123.deny
   ```

   The script refuses to render while the title or body contains a denied term, a
   non-OpenHands email address, or a link to Linear, HappyFox, Slack, Notion,
   Google Docs, or Granola. Fix the draft and re-run; never trim the deny file to
   pass the check.

### Step 4: Ask for approval

1. Get the conversation link:

   ```bash
   python3 $S conversation-url --host <OpenHands app URL from the HOST context>
   ```

   If it fails, ask the user for the conversation URL instead of guessing.
2. For each drafted ticket, post the approval comment from
   `references/templates.md` with `save_comment` (`issueId: <LINEAR-ID>`). It holds
   only the @mention, the link, and the AI note: no draft text, no aliases.
3. In the conversation, show each draft using the "Draft presentation" template:
   target, alias mapping, and the dry-run output verbatim. Then **stop and wait**.

Approval must name the ticket ("approve PRD-123", "approve all"). Anything else is
not approval. When the user asks for changes, edit the files, re-run the dry run,
show the new output, and wait again. Do not post another Linear comment for
revisions.

### Step 5: Write to GitHub (only after approval)

For each approved ticket:

1. Call `get_issue` again. If the Linear description changed since the draft, show
   that, redraft, and ask again.
2. Run the same command as the approved dry run **without `--dry-run`**. Keep
   every other argument the same.
   - `create` prints `{"number", "url", "version": 1}`.
   - `update` rewrites the body, appends `vN · <date> · Updated from Linear <ID>` to
     the sync history, and posts a short version comment on the GitHub issue so
     watchers are notified.
3. For **Create** only, link the new issue to Linear as a plain link, not the native
   sync: `save_issue` with `id: <LINEAR-ID>` and
   `links: [{url: <github url>, title: "OpenHands/enterprise#<N>"}]`.
4. Remove the label: `save_issue` with `id: <LINEAR-ID>` and
   `removeLabels: ["feedback-github-sync"]`.
5. Post the completion comment from `references/templates.md`.

If a GitHub write fails, keep the label and report the error. Do not retry with
changed text without showing it to the user again.

### Step 6: Summarize

Report, per ticket: created or updated (with GitHub link and version), skipped
(with reason), or waiting for approval. Then `rm -rf /tmp/feedback-sync`.

## Rules

- Never write to GitHub without approval of the exact dry-run text in this
  conversation.
- Never post the Linear URL, the alias mapping, or un-anonymized text to GitHub.
- Never put draft text on Linear; the approval comment has only the link.
- Remove the label only after the GitHub write succeeds.
- Use only the `bug` and `enhancement` labels on new issues; no assignee.

## Additional resources

- **`references/anonymization.md`**: what to replace, where names hide, alias
  rules, and the deny-terms file.
- **`references/templates.md`**: issue body, sync history format, Linear comments,
  and the draft presentation.
- **`scripts/feedback_sync.py`**: `links`, `conversation-url`, `check-leaks`,
  `create`, `update`. Run with `--help` for arguments.
