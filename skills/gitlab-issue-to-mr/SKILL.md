---
name: gitlab-issue-to-mr
description: >
  Create an automation that implements GitLab issues when a configurable
  trigger label is applied. Polls one or more repositories deterministically,
  clones the default branch, starts one OpenHands conversation per label event,
  then commits, pushes, and opens the merge request itself.
triggers:
  - /issue-to-mr:setup
---

# GitLab Issue to MR Automation

Create a cron automation that watches one or more GitLab repositories for issues
with a trigger label, starts an OpenHands conversation once per label event with
the repository's default branch already checked out, and opens a merge request
with whatever the agent produced.

The automation script is deterministic: issue discovery, label-event tracking,
state persistence, the clone, the branch, the commit, the push, the merge request,
the issue comments, and the clone's removal are all handled in Python. The LLM is
invoked only to write the code.

The agent is told **which** issue to implement, not what it says. It fetches the
description, the discussion, and whatever they link to itself, so nothing in the
prompt goes stale between dispatch and the moment the agent reads it.

That needs read access, so the conversation is handed exactly one secret,
`GITLAB_TOKEN`, and no MCP servers. `AGENT_SECRET_NAMES` stays an allow-list: the
rest of the deployment's secret store is not reachable from a conversation whose
instructions came from an issue.

The agent also finishes the job: it commits, pushes its branch, and opens the
merge request, so the merge request appears when the agent stops rather than on the
next poll. The script does not trust that it happened - when the conversation
ends it asks GitLab whether the merge request exists, and opens it itself when it
does not. `origin` still carries no credential, so every GitLab command the agent
runs has to name `GITLAB_TOKEN`; the SDK only puts a secret in the environment of a
command that mentions it, and masks it in the output.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings -> Secrets**:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITLAB_TOKEN` | Personal Access Token | `api` scope (full API access) |

The `api` scope covers everything the automation needs: reading issues and label
events, posting notes, pushing branches, and opening merge requests. A
read-only token will poll happily and then fail at the point of pushing.

For self-hosted GitLab, also set `GITLAB_API_URL` to your instance's API endpoint
(e.g. `https://gitlab.example.com/api/v4`). If not set, the automation defaults to
`https://gitlab.com/api/v4`.

Check with:
```bash
curl -s "https://gitlab.com/api/v4/user" \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('username') or d.get('message'))"
```

If the token is missing or invalid, inform the user and stop.

---

## Setup Workflow

Follow these steps in order.

### Step 1 - Verify `GITLAB_TOKEN`

Ask the user whether they are using `gitlab.com` or a self-hosted GitLab instance.
If self-hosted, ask for the GitLab host URL (e.g. `https://gitlab.example.com`).

Record the GitLab host URL. Derive the API URL from it:
- `https://gitlab.com` → `https://gitlab.com/api/v4`
- `https://gitlab.example.com` → `https://gitlab.example.com/api/v4`

Run the `curl` check against the correct API URL:

```bash
curl -s "{api_url}/user" \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('username') or d.get('message'))"
```

- If absent: *"GITLAB_TOKEN is not set. Please add it in
  OpenHands Settings -> Secrets."* Stop.
- If the API returns `{"message": "401 Unauthorized"}`: tell the user the token is
  invalid and ask them to update it. Stop.

If self-hosted and `GITLAB_API_URL` is not already set as a secret, instruct the
user to add it in OpenHands Settings -> Secrets so the automation can use it at
runtime. The script reads `GITLAB_API_URL` from the secret store at startup and
falls back to `https://gitlab.com/api/v4` when it is absent.

### Step 2 - Collect repositories

Ask: *"Which GitLab repositories should be watched?
(Format: `group/project`, e.g. `my-group/backend`. For subgroups, use the full
path: `group/subgroup/project`. List several separated by commas to serve them
all from one automation.)"*

Validate access to **each** repository, and confirm the token can push:
```bash
curl -s "{api_url}/projects/{url_encoded_path}" \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'message' in d:
    print('ERROR:', d['message'])
else:
    print(f\"Accessible. Default branch: {d.get('default_branch')}.\")
"
```

Record every accepted repository into `REPOS = ["{group/project}", ...]`. If one
repository fails the check, say which and ask whether to continue without it.

Each repository is polled independently and keeps its own state, so issue IIDs
never collide between them. The trigger label, branch prefix, and schedule are
shared; a repository needing different settings wants its own automation.

### Step 3 - Collect trigger label

Ask: *"Which issue label should trigger an implementation?
(Press Enter for the default: `openhands`.)"*

Record the answer as `TRIGGER_LABEL`. If the label does not exist yet, tell the
user that GitLab will still record the event once the label is created and
applied to an issue.

The automation works an issue when it sees the latest matching label-added
`resource_label_event` for that label. To ask for another attempt later, remove
and re-apply the label - that opens a second branch and a second merge request
rather than overwriting the first.

### Step 4 - Collect the merge request mode

Ask: *"Should the merge requests be opened as drafts?
  1. Draft (default) - opened as a draft, ready for a human to mark ready
  2. Ready for review - opened as a normal merge request
(Press Enter for Draft)"*

Map the choice to `DRAFT_MERGE_REQUEST` (`True` or `False`).

### Step 5 - Collect the branch prefix

Ask: *"What branch prefix should the automation use?
(Press Enter for the default: `openhands/issue`, which produces
`openhands/issue-42`.)"*

Record as `BRANCH_PREFIX`. Keep it free of spaces and of characters git rejects
in a ref name.

### Step 6 - Collect cron schedule

Ask: *"How often should the automation poll for labelled issues?
(Press Enter for the default: every 5 minutes.
Use a cron expression for a different interval, e.g. `0 * * * *` = hourly)"*

Default: `*/5 * * * *`.

Record as `CRON_SCHEDULE`.

### Step 7 - Confirm the secret scope

The agent is handed `GITLAB_TOKEN`, because it reads the issue and its discussion
itself. Ask: *"Beyond the GitLab token, does the repository's build need a secret
of its own - a package registry token, for example? (Press Enter for none.)"*

Record the answers appended to the default, as
`AGENT_SECRET_NAMES = ["GITLAB_TOKEN", "NAME", ...]`.

Keep it an allow-list. Forwarding the whole secret store would put every
credential in the deployment behind a prompt written by whoever opened the issue.
If the repositories are public and you would rather the conversation held no
credential at all, set the list to `[]` - the agent can still read a public issue
unauthenticated, and private repositories then stop working.

### Step 8 - Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly these constant
substitutions near the top of the file:

> The script also reads a `config.json` shipped beside it, if there is one, over
> these constants. That is how a catalog entry would configure an unmodified copy.
> This setup path substitutes the constants and ships no `config.json`, so the
> two never collide.

| Placeholder | Replace with |
|---|---|
| `REPOS = ["group/project"]` | `REPOS = ["{group/project}", ...]` - one entry per repository collected in Step 2 |
| `TRIGGER_LABEL = "openhands"` | `TRIGGER_LABEL = "{trigger_label}"` |
| `BRANCH_PREFIX = "openhands/issue"` | `BRANCH_PREFIX = "{branch_prefix}"` |
| `DRAFT_MERGE_REQUEST = True` | `DRAFT_MERGE_REQUEST = {True or False}` |
| `AGENT_SECRET_NAMES: list[str] = ["GITLAB_TOKEN"]` | `AGENT_SECRET_NAMES: list[str] = ["{name}", ...]` |
| `DEFAULT_GITLAB_API_URL = "https://gitlab.com/api/v4"` | `DEFAULT_GITLAB_API_URL = "{api_url}"` - the GitLab API URL collected in Step 1 |
| `DEFAULT_GITLAB_HOST = "gitlab.com"` | `DEFAULT_GITLAB_HOST = "{gitlab_host}"` - the host derived from the URL |

Leave `MAX_NEW_PER_RUN` and `DEFAULT_OPENHANDS_URL` alone unless the user asks
for a different cap or a non-default OpenHands URL.

For self-hosted GitLab, the `DEFAULT_GITLAB_API_URL` and `DEFAULT_GITLAB_HOST`
constants are set directly in the script. The script also checks for a
`GITLAB_API_URL` secret at runtime (which takes precedence), so either path
works - but substituting the constants means the automation works even when the
secret is not set.

A repository may be given as `group/project`, as a clone URL, or as an SSH remote;
the script normalizes each one at startup and names the value it could not read
rather than blaming the token.

Use a safe string writer such as `json.dumps(value)` when inserting user-provided
repository names, labels, or prefixes into Python string literals.
`json.dumps(list_of_repos)` produces the whole `REPOS` list safely in one step.

Write the customized script to a temporary build directory:
```bash
mkdir -p /tmp/issue-to-mr-build
# write the customized main.py to /tmp/issue-to-mr-build/main.py
```

Validate syntax before packaging:
```bash
python3 -m py_compile /tmp/issue-to-mr-build/main.py && echo "Syntax OK"
```

Fix any syntax errors before proceeding.

### Step 9 - Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- **OPENHANDS_HOST**: the Automation backend `url_from_agent`
- **Auth**: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

```bash
tar -czf /tmp/issue-to-mr.tar.gz -C /tmp/issue-to-mr-build .

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=gitlab-issue-to-mr" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/issue-to-mr.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

### Step 10 - Register the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"GitLab Issue to MR: {repo_summary} label {trigger_label}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"{cron_schedule}\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 900
  }" | python3 -m json.tool
```

Use the single repository as `{repo_summary}` when there is one, and something
like `3 repos` when there are several. A poll clones a repository per queued
issue and pushes finished branches, so the timeout allows for that; a run never
waits for an agent to finish, only for it to be started.

Record the returned `id`.

### Step 11 - Confirm

Tell the user:

> ✅ **GitLab Issue to MR** is running!
>
> - Automation ID: `{id}`
> - GitLab host: `{gitlab_host}`
> - Repositories: `{group/project}`, ... (one line each)
> - Trigger label: `{trigger_label}`
> - Branch prefix: `{branch_prefix}`
> - Merge requests: `{draft or ready for review}`
> - Polling schedule: `{cron_schedule}`
> - State file per repository:
>   `~/.openhands/workspaces/automation-state/gitlab_issue_to_mr_{id}_{group}__{project}.json`
>
> Apply the `{trigger_label}` label to an issue to queue an implementation. Each
> label event is processed once. To ask for another attempt, remove and re-apply
> the label - that opens a second branch and merge request.
>
> The agent runs without GitLab credentials; the automation pushes the branch and
> opens the merge request once the agent has stopped.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which loads `config.json` if one was shipped,
checks that `git` is available, resolves `GITLAB_API_URL` (from config, the
`GITLAB_API_URL` secret, or the default), resolves and validates `GITLAB_TOKEN`
once, then processes every repository in `REPOS` independently. One repository
failing does not stop the others; the run fails only if every repository fails.

For each repository:

1. Loads that repository's state (see `references/state-schema.md`) and reads its
   default branch.
2. Lists open issues carrying `TRIGGER_LABEL`, newest-updated first.
3. For each labelled issue, up to `MAX_NEW_PER_RUN` new ones per run:
   - Refetches the issue so a label removed since the listing does not start work.
   - Finds the latest matching GitLab label-added `resource_label_event`, and
     skips it if that event has already been tracked.
   - Picks the first free branch name, `{BRANCH_PREFIX}-{iid}` or a numbered
     variant of it.
   - Clones the default branch, shallow and single-branch, into
     `{WORKSPACE_BASE}/issue-to-mr/{group}__{project}/issue-{iid}-{event_id}`,
     sets the commit identity, and creates the branch. `origin` keeps its plain
     HTTPS URL, so the workspace holds no credential.
   - Starts an OpenHands conversation **whose working directory is that clone**,
     with the issue title and URL in the prompt, and only the secrets named in
     `AGENT_SECRET_NAMES` attached.
   - Comments on the issue (via GitLab notes) with the branch, the label event,
     and the conversation link.
   - Records the task with `status: "active"`.
   - If the clone or the conversation cannot be created, the clone is removed and
     nothing is recorded, so the next poll retries the label event.
4. For each active task:
   - Abandons a conversation that has not reached a terminal status within two
     hours, comments on the issue, and reclaims its clone.
   - When the conversation reaches `idle`, `finished`, `error`, or `stuck`:
     - Adopts the merge request the agent opened, if GitLab says one exists for
       the branch, and comments its link on the issue. Everything below is the
       path taken when it does not.
     - Skips the merge request if the issue was closed meanwhile.
     - Reports the problem on the issue if the conversation ended in `error` or
       `stuck`.
     - Commits whatever the agent left uncommitted, on top of any commits it made
       itself.
     - Posts the agent's answer on the issue, and opens no merge request, when
       there are no commits at all - that is how an agent reports an issue too
       ambiguous to implement.
     - Otherwise pushes the branch, opens the merge request (draft by default,
       titled `[!42] <issue title>`, with the agent's summary and `Closes #42` in
       the description), and comments the link on the issue.
     - A push or merge request that fails is retried on the next two polls before
       the task is reported as failed, so a transient GitLab error does not throw
       the work away.
5. Removes the clone of every finished task, but only after confirming the
   conversation has stopped - deleting it under a running agent would remove its
   working directory. When that cannot be confirmed the directory is left alone
   and the next poll tries again.
6. Saves that repository's state atomically.

The completion callback fires once for the whole run.

---

## Additional Resources

- **`references/state-schema.md`** - State JSON schema, field definitions, and the
  task lifecycle.
- **`scripts/main.py`** - The complete automation script. Customize the constants
  at the top before packaging.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Nothing is ever queued | Trigger label not present on any issue | Apply the configured label to an issue |
| "401 Unauthorized" in run logs | Token expired or invalid | Rotate and update `GITLAB_TOKEN` |
| 404 on project access | Project path wrong or no access | Re-check the entry in `REPOS` and the token's permissions |
| Push fails | Token lacks `api` scope or write permission | Issue a token with `api` scope |
| `git is not available in the automation runtime` | The runtime image has no git | Use a runtime image that ships git |
| Issue commented "did not change any code" | The agent judged the issue too ambiguous, or made no edits | Read its answer in the comment, add the missing detail to the issue, then re-apply the label |
| Same issue not picked up again after new comments | Its label event was already processed | Remove and re-apply the trigger label |
| Agent reports it cannot push or open an MR | By design - it has no credentials | No action; the automation pushes and opens the merge request after the agent stops |
| A backlog of labelled issues starts slowly | `MAX_NEW_PER_RUN` caps how many conversations one poll starts | Wait for the next polls, or raise the cap in the script |
| Clones remain under `issue-to-mr/` | Their conversations had not stopped yet | They are removed by a later poll once the conversation is terminal |
| API calls go to gitlab.com but repo is self-hosted | `GITLAB_API_URL` not set or config not substituted | Set `GITLAB_API_URL` secret or ensure `DEFAULT_GITLAB_API_URL` was substituted in the script |
