# public-skills

A collection of reusable AI-agent **skills** for the [OpenHands](https://github.com/All-Hands-AI/OpenHands) ecosystem. Each skill lives in its own directory under [`skills/`](skills/) and is built for **progressive disclosure**: a concise `SKILL.md` front door (with a name and trigger description in YAML front matter), optional `commands/` for slash-command triggers, `references/` for deeper documentation, and `scripts/` for deterministic helper code.

## Repository layout

```
.
├── .gitignore
└── skills/
    ├── concise-prd/              # Lightweight PRD generator
    ├── customer-feedback/        # Log feedback as a Linear ticket
    ├── gitlab-issue-to-mr/       # Cron automation: GitLab issue → code → merge request
    ├── linear-github-sync/       # Sync Linear feedback tickets to GitHub, anonymized
    ├── multi-agent-orchestrator/ # Boss/Worker pattern for parallel agent work
    └── prd-interview/            # Interview-driven PRD authoring
```

Each skill shares a common structure:

| Path | Purpose |
|------|---------|
| `SKILL.md` | The skill itself: when to use it, the workflow, and the exact steps to follow. Front matter holds the `name` and `description` used for activation. |
| `commands/<name>.md` | Slash-command variant (e.g. `/prd-interview`), used when the skill starts from a command rather than a keyword. |
| `references/` | Supporting documentation: schemas, templates, patterns, and background. |
| `scripts/` | Deterministic helper programs (Python/Bash) that do the exact work the skill describes. |
| `README.md` | Optional per-skill overview and quick-start. |
| `.plugin/plugin.json` | Plugin metadata (name, version, description, author, license, keywords). |
| `.codex-plugin` / `.claude-plugin` | Marker files that expose the skill to other agents. |

## Skills

### [prd-interview](skills/prd-interview/)

Turns raw context — a text blob, a Notion page, or a Linear ticket — into a concise PRD (**Problem**, **User Scenarios**, **I Can**) by interviewing the user one question at a time. For Linear sources it restructures the ticket so the PRD sits on top and the original body is preserved verbatim under an `# Original Feedback` heading. Enforces a *Draft-First Rule*: nothing is written back to Linear or Notion until the user approves a locally saved draft.

### [concise-prd](skills/concise-prd/)

Generates a lightweight, focused PRD with exactly five sections: **User Problem**, **Scenarios**, **I Can Statements**, **Why It Matters**, and a conditional **Customer Evidence** section. Prioritizes brevity and user-centric language, and asks for clarification instead of inventing missing details.

### [customer-feedback](skills/customer-feedback/)

Logs customer feedback as a Linear issue in the Product team's **Triage** state with the `customer-feedback` label. When a customer name is detected, it also creates or associates a **Customer Request** via Linear's GraphQL API. Includes a full end-to-end shell example.

### [multi-agent-orchestrator](skills/multi-agent-orchestrator/)

Implements a **Boss/Orchestrator** pattern: one coordinating agent decomposes a PRD into parallel tasks, launches **Worker** sub-conversations through the Agent Canvas API, monitors their status, and coordinates QA and code review. Users always keep direct access to every worker conversation. Ships two helper scripts (`delegate.sh`, `monitor.sh`) and reference docs on delegation patterns and an SDLC workflow.

### [gitlab-issue-to-mr](skills/gitlab-issue-to-mr/)

Deploys a **cron automation** that watches one or more GitLab repositories for issues with a configurable trigger label (default `openhands`). For each label event it clones the default branch, starts one OpenHands conversation that implements the issue, then commits, pushes, and opens a **draft merge request** itself — so the agent never needs GitLab push credentials. The deterministic `scripts/main.py` handles discovery, state persistence (KV store with file fallback), exactly-once processing, and an agent-final answer when no code was produced.

### [linear-github-sync](skills/linear-github-sync/)

Copies Linear tickets labeled `linear-github-sync` (teams **OHE** and **PRD**) into issues in the public `OpenHands/enterprise` repository — **anonymized**. Customer names become `AlphaCo`, `BetaCo`, ... and people become their roles; a deny-list leak check blocks any write that still contains a real name, email, or private link. Nothing is written to GitHub until the user approves the exact rendered draft, and versioned sync history is maintained on every update.

## Quick start

Skills are projects/plugins that agents and automation load from this repository:

1. **Browse** a skill's `SKILL.md` to understand when and how to use it.
2. **Invoke** skills defined as commands via their slash command (e.g. `/prd-interview`).
3. **Deploy** automation skills (e.g. `gitlab-issue-to-mr`) by following their `SKILL.md` setup workflow, which packages and registers the cron automation.

## Contributing

Add a new skill by creating a directory under `skills/` with a `SKILL.md` file whose front matter includes a `name` and a trigger `description`. Follow the structure of the existing skills (commands, references, scripts as needed) and keep the `SKILL.md` as the concise front door with the details revealed step by step.