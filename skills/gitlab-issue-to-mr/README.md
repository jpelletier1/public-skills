# GitLab Issue to MR

Create an automation that implements GitLab issues when a configurable trigger
label is applied, and opens the merge request for you.

## Trigger

This skill is activated by:

- `/issue-to-mr:setup`

## Features

- Implements an issue on demand by watching for a GitLab label-added event
- Supports both `gitlab.com` and self-hosted GitLab deployments
- Watches several repositories from a single automation, each with its own state
- Processes each label application exactly once, with persistent state
- Re-runs on demand by removing and re-applying the label, on a fresh branch
- Clones the default branch for the agent, and removes the clone when the task
  ends, so nothing accumulates between runs
- Lets the agent open the merge request, and opens it in Python when the agent did not
- Opens draft merge requests by default, titled `[!42] <issue title>`, with the
  agent's summary and `Closes #42` in the description
- Comments on the issue when work starts, when it finishes, and when it does not
- Posts the agent's answer instead of a merge request when it made no changes
- Caps how many conversations one poll starts, so a labelled backlog does not
  start dozens at once

## What the agent is told, and what it can reach

The prompt names the repository, the issue IID and title, and its URL. The
agent fetches the description, the discussion, and anything they link to itself -
a copy pasted at dispatch would already be stale, and it would stop where the
issue's own text stops.

Reading that needs credentials, so the conversation is handed exactly one secret,
`GITLAB_TOKEN`, and none of the deployment's MCP servers.
`AGENT_SECRET_NAMES` is an allow-list, so the rest of the secret store stays out
of reach of a conversation whose instructions came from an issue. Set it to `[]`
for public repositories if you would rather it held nothing.

The agent commits, pushes its branch, and opens the merge request itself, so it
appears as soon as the agent stops instead of waiting for the next poll. The
script verifies that on GitLab rather than trusting the agent's word, and opens
the merge request itself when the agent did not - a failed push or a dead
conversation never loses the work. `origin` carries no credential, so each GitLab
command has to name `GITLAB_TOKEN`, which the SDK injects only into a command
that mentions it and masks in the output.

## Prerequisites

Set `GITLAB_TOKEN` in OpenHands Settings -> Secrets. The token must be a GitLab
Personal Access Token with:

- **api** scope (read/write the GitLab API)
- Permission to read the repositories, read and write issues (for the progress
  comments), **write repository** (to push the branch), and **open merge requests**

For self-hosted GitLab, also set `GITLAB_API_URL` to your instance's API endpoint
(e.g. `https://gitlab.example.com/api/v4`). If not set, the automation defaults to
`https://gitlab.com/api/v4`.

The automation runtime must have `git` available; the script clones, commits, and
pushes with it.

## Quick Start

Ask OpenHands:

> "Set up an issue-to-MR automation for my `my-group/backend` repo using the
> `openhands` label."

After setup, apply the configured label to an issue to queue an implementation.
To ask for another attempt later, remove and re-apply the label.

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
- [references/state-schema.md](references/state-schema.md) - State document and
  task lifecycle
