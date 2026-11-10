---
name: prd-interview
description: This skill should be used when the user asks to "interview me for a PRD", "run a PRD interview", "turn this ticket into a PRD", "write a PRD for this Linear ticket", "/prd-interview", or provides context (a text blob, Notion page, Linear ticket) and wants help shaping it into a concise PRD. Analyzes the context, interviews the user one question at a time with a visible count of remaining questions, and produces a concise PRD (Problem, User Scenarios, I Can statements). For Linear tickets, preserves the original body under an "Original Feedback" H1 and prepends the PRD. Always creates a draft for review before updating any Linear ticket or doc.
---

# PRD Interview Skill

Turn raw context (feedback, a ticket, a doc, a Slack thread) into a concise PRD by analyzing what is already known and interviewing the user to fill the gaps.

The PRD has exactly three sections:

| Section | Length | Focus |
|---------|--------|-------|
| Problem | 1-3 sentences | The user's pain, not the solution |
| User Scenarios | 2-5 bullets | Who hits the problem, in what situation |
| I Can | 3-7 bullets | User-visible acceptance criteria ("I can ...") |

## When to Use

- "Interview me to write a PRD for ..."
- "Turn this Linear ticket into a PRD"
- "/prd-interview <text | Notion link | Linear link/ID>"
- The user pastes feedback or a link and wants a PRD shaped through Q&A

## Draft-First Rule

**Never update a Linear ticket, Notion page, or any other doc without first creating a draft and getting the user's explicit approval.**

For every write:
1. Write the complete proposed content to a local draft file at `/tmp/prd-interview/<source-id>.md` (e.g. `PROD-123.md`, or a short slug for non-ticket sources).
2. Show the user the full draft and a one-line summary of what will change (e.g. "Prepends Problem / User Scenarios / I Can; moves the current body under `# Original Feedback` unchanged").
3. Ask: "Apply this draft to <target>? (yes / edit / no)".
4. Write to the target only after a clear "yes". On "edit", revise the draft and show it again. On "no", leave the target untouched; the draft file stays available.
5. Immediately before writing, re-fetch the target. If it changed since it was loaded, tell the user, rebuild the draft from the latest version, and ask again.

The interview itself only updates the local draft. It never writes to the target.

## Workflow

1. Gather context (Step 1)
2. Analyze and draft (Step 2)
3. Linear sources: draft the restructured ticket and apply it after approval (Step 3)
4. Interview the user, updating the local draft after each answer (Step 4)
5. Finalize: show the final draft and apply it after approval (Step 5)

### Step 1: Gather Context

Identify the source type and load its full content:

| Input | How to load |
|-------|-------------|
| Pasted text | Use as-is |
| Linear URL or identifier (e.g. `PROD-123`, `linear.app/.../issue/PROD-123/...`) | See [Loading a Linear ticket](#loading-a-linear-ticket) |
| Notion URL | See [Loading a Notion page](#loading-a-notion-page) |
| Other URL | Fetch with `curl`; use a browser only if the page needs JS |

Also read any comments, linked customer requests, or attachments on the source when available. They often have the best evidence for the Problem and Scenarios.

If the source cannot be loaded (missing credentials, no access), say so and ask the user to paste the content instead. Do not guess.

### Step 2: Analyze and Draft

Before asking anything, extract everything the context already answers:

1. Write a **draft PRD** filling each section with what the context supports. Mark unsupported content as `_TBD_` rather than inventing it. Save it to the local draft file.
2. Build the **question list**: one question per material gap or ambiguity, ordered by impact (Problem first, then Scenarios, then I Can). Typical gaps:
   - Who exactly is the user (role, persona, plan tier)?
   - What is the underlying problem vs. the requested solution?
   - What do users do today (workaround) and what does it cost them?
   - Which scenarios matter most / which are out of scope?
   - What must a user be able to do for this to be considered done?
   - Edge cases or constraints that change the acceptance criteria
3. Keep the list short: aim for **3-7 questions**. Don't ask about things the context already answers. Confirm those in the draft instead.

Show the user a brief analysis:

```
**What I understood:** <2-3 sentence summary of the context>

**Draft PRD:** <draft with _TBD_ markers>

I have **N questions** to fill the gaps.
```

### Step 3: Restructure the Linear Ticket (Linear sources only)

Build the restructured description so the PRD sits on top and the original body is preserved verbatim at the bottom:

```markdown
# Problem

<draft or _TBD_>

# User Scenarios

- <draft or _TBD_>

# I Can

- I can <draft or _TBD_>

# Original Feedback

<original ticket body, unchanged>
```

Rules:
- **Never modify or drop the original body.** Copy it byte-for-byte under `# Original Feedback`.
- **Idempotency:** if the description already contains a `# Original Feedback` heading, the ticket was restructured before. Keep everything from `# Original Feedback` downward as-is and only replace the PRD sections above it. Use the existing PRD content as the starting draft.
- If the original body is empty, put `_No original description._` under `# Original Feedback`.

Follow the [Draft-First Rule](#draft-first-rule): save this as the draft, show it, and apply it to the ticket only after the user approves. Then start the interview. If the user declines, start the interview anyway. Everything is applied together in Step 5.

### Step 4: Interview

Ask **one question at a time**. Every question must show progress and offer a suggested answer drawn from the context so the user can simply confirm:

```
**Question 2 of 5** · 3 remaining · _Section: User Scenarios_

<question>

**Suggested answer:** <best guess from context, or "None — no signal in the context">

(Reply with your answer, "yes" to accept the suggestion, "skip", or "done" to finish now.)
```

After each answer:
1. Update the local draft file with the answer. Do **not** write to the ticket or doc.
2. Re-evaluate the remaining questions. Drop questions the answer already resolved. Add a new one only if the answer exposed a material gap. When the total changes, say so (e.g. "That covered question 4 too. **2 remaining**").
3. Move to the next question.

Handling replies:
- **"yes"**: accept the suggested answer.
- **"skip"**: leave that part as `_TBD_` and continue.
- **"done"**: stop the interview and go to Step 5 with the current draft.
- Vague answers: ask at most one short follow-up for that question, then move on.

### Step 5: Finalize

1. Polish the draft: tighten wording, remove duplicates, make every "I can" statement specific and testable, and keep the Problem free of solution language.
2. Save the final draft and show it in full, listing any remaining `_TBD_` items.
3. Deliver it, following the [Draft-First Rule](#draft-first-rule):
   - **Linear source:** ask to apply the final draft to the ticket (Step 3 structure, original feedback untouched). On approval, write it and share the URL.
   - **Notion or other doc source:** output the PRD as markdown in chat and offer to write it to the doc, a file, or a new/existing Linear ticket. Write only after approval. When writing to a Linear ticket, use the Step 3 structure with the original context under `# Original Feedback`.
   - **Pasted text:** output the PRD in chat and offer the same destinations.
4. Once the PRD is applied (or the user declines), tell the user where the draft file is. Delete it only if they ask.

## Writing Guidelines

- **Problem:** describe the pain from the user's perspective in 1-3 sentences. Write "Users can't X, so they Y", not "We need to build Z".
- **User Scenarios:** concrete situations with a who and a when, e.g. "A support engineer triaging 50 tickets on Monday morning needs to ...".
- **I Can:** user-visible outcomes, one capability per bullet, verifiable by a tester. Avoid implementation details (APIs, tables, frameworks).
- Use the user's and customer's own words where possible.
- Never invent customer quotes, data, or requirements. Unknowns stay `_TBD_`.

## Loading a Linear Ticket

Prefer Linear MCP tools when available:
- Read: `get_issue` with the identifier (e.g. `PROD-123`); `list_comments` for discussion.
- Write (only after draft approval): `save_issue` with `id` and the full new `description`.

Otherwise use the GraphQL API with `LINEAR_API_KEY` (ask the user for it if not set). Lookups accept the human identifier:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query":"query($id:String!){ issue(id:$id){ id identifier title url updatedAt description comments{ nodes{ body user{ name } } } } }","variables":{"id":"PROD-123"}}' \
  | jq '.data.issue'
```

Save `updatedAt` so you can detect concurrent edits before writing (Draft-First Rule, item 5).

Apply an approved draft. Build the payload with `jq` so markdown is escaped safely:

```bash
jq -n --arg id "PROD-123" --rawfile desc /tmp/prd-interview/PROD-123.md \
  '{query:"mutation($id:String!,$d:String!){ issueUpdate(id:$id, input:{description:$d}){ success issue{ url } } }",variables:{id:$id,d:$desc}}' \
| curl -s -X POST https://api.linear.app/graphql \
    -H "Content-Type: application/json" \
    -H "Authorization: $LINEAR_API_KEY" \
    -d @- | jq '.data.issueUpdate'
```

## Loading a Notion Page

Prefer Notion MCP tools when available. Otherwise use the REST API with `NOTION_API_KEY`. The page ID is the trailing 32-character hex string in the URL.

```bash
PAGE_ID="<32-char id from URL>"
curl -s "https://api.notion.com/v1/blocks/$PAGE_ID/children?page_size=100" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  | jq -r '.results[] | .[.type].rich_text? // empty | map(.plain_text) | join("")'
```

Follow `next_cursor` (pass `&start_cursor=...`) when `has_more` is true. If the API returns 404, the page probably isn't shared with the integration. Ask the user to share it or paste the content.

Writing to Notion follows the Draft-First Rule. Append the PRD as new blocks (`PATCH /v1/blocks/$PAGE_ID/children`) rather than deleting existing content, unless the user explicitly asks to replace it.
