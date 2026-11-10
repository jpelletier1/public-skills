# public-skills

A collection of reusable AI-agent skills for [OpenHands](https://github.com/All-Hands-AI/OpenHands). Each skill lives in its own directory under [`skills/`](skills/) and packages an agent behavior as a `SKILL.md` plus any commands, references, and scripts it needs.

## Layout

```
public-skills/
├── README.md
└── skills/
    ├── concise-prd/             # Generate lightweight PRDs
    ├── customer-feedback/       # Log feedback as Linear issues
    ├── gitlab-issue-to-mr/      # Automate GitLab issues → merge requests
    ├── linear-github-sync/      # Sync Linear tickets → GitHub issues
    ├── multi-agent-orchestrator/  # Boss/worker multi-agent orchestration
    └── prd-interview/           # Interview users into concise PRDs
```

## Skills

### concise-prd

Generates lightweight, focused Product Requirements Documents with a consistent structure: user problem, scenarios, "I can" acceptance criteria, why it matters, and optional customer evidence. Invoke with `/concise-prd` or a plain-language request to create a concise PRD.

### customer-feedback

Creates a Linear feedback ticket in the Product team's Triage state with the `customer-feedback` label. When a customer name is detected, it also creates or associates a Customer Request in Linear. Invoke with `/customer-feedback`.

### gitlab-issue-to-mr

Deploys a cron automation (backed by `scripts/main.py`) that watches one or more GitLab repositories for issues with a configured trigger label. Each label event starts an OpenHands conversation that implements the issue; the automation clones the default branch, pushes the resulting branch, opens a (draft) merge request, and comments on the issue. Includes persistent per-repository state (`references/state-schema.md`).

### linear-github-sync

Copies Linear tickets labeled `linear-github-sync` (from the **OHE** and **PRD** teams) into public GitHub issues in `OpenHands/enterprise`. It anonymizes customer names (see `references/anonymization.md`), drafts the issue body with a versioned sync history, asks for approval through a Linear comment, and only then writes to GitHub and removes the label. Deterministic helpers live in `scripts/feedback_sync.py`.

### multi-agent-orchestrator

Implements a Boss/Worker orchestration pattern: a single orchestrating agent decomposes a PRD into parallel tasks, delegates each one to a worker sub-conversation (via `scripts/delegate.sh`), monitors progress (`scripts/monitor.sh`), and coordinates QA and code review across a three-phase SDLC workflow.

### prd-interview

Turns raw context (pasted text, a Notion page, or a Linear ticket) into a concise PRD by analyzing what is already known and interviewing the user one question at a time. Always drafts before writing, never mutates the original content, and preserves a Linear ticket's original body under an `# Original Feedback` heading.

## Using a skill

Skills are loaded by the client that consumes them (e.g. OpenHands or Claude Code). Each skill directory follows the same pattern:

- `SKILL.md` — front-matter (`name`, `description`, optional `triggers`) plus the full skill instructions
- `commands/` — slash-command wrappers that activate the skill
- `references/` — supporting documentation
- `scripts/` — helper scripts invoked by the skill
- `.plugin/` — plugin manifest (for skills that ship as plugins)

## Contributing

To add a skill, create a `skills/<skill-name>/` directory with a `SKILL.md` that includes descriptive front-matter and instructions, then any supporting commands, references, and scripts.