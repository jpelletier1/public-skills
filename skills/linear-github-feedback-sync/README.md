# Linear → GitHub Feedback Sync

Copy Linear feedback tickets into the public `OpenHands/enterprise` repository,
anonymized, after you approve the exact text.

## Trigger

- `/feedback-github-sync`, or ask to "sync feedback tickets to GitHub"

## How it works

1. Finds tickets labeled `feedback-github-sync` in the **OHE** and **PRD** Linear teams.
2. For each ticket, checks for an attached `OpenHands/enterprise` issue:
   - none: drafts a new issue (`bug` or `enhancement`, no assignee)
   - one: drafts a new body for it, with the next version in a "Sync history" block
   - one that Linear's native GitHub sync manages: skips it and tells you why
3. Replaces customer names with AlphaCo, BetaCo, ... and people with their roles.
   A deny-list check blocks the write if a real name, email, or private link remains.
4. Comments on the Linear ticket with only a link to the conversation, and waits.
5. After you reply "approve <ID>": writes to GitHub, removes the label, and comments
   the GitHub link on Linear.

## Requirements

- Linear MCP connected
- `GITHUB_TOKEN` with issue write access to `OpenHands/enterprise`
- `LINEAR_API_KEY` (recommended, used to detect native-synced tickets)
