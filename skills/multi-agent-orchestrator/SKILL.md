---
name: multi-agent-orchestrator
description: This skill should be used when the user asks to "orchestrate multiple agents", "manage multi-agent workflow", "coordinate sub-conversations", "delegate work to multiple agents", "run a boss/worker agent pattern", or describes a PRD that needs decomposition into parallel tasks. Enables a single Orchestrator (Boss) agent that decomposes requirements and launches Worker sub-conversations.
---

# Multi-Agent Orchestrator

This skill enables a **Boss/Orchestrator** pattern where a single coordinating agent manages multiple **Worker** sub-conversations, each working independently on different tasks or repositories.

## Core Architecture

### The Boss (Orchestrator) Agent

The orchestrator agent operates as follows:

1. **Accept Requirements**: Receive PRD as free text, markdown file path, or URL to Jira/Linear ticket
2. **Decompose**: Break down requirements into discrete, parallelizable tasks
3. **Plan**: Decide how many workers needed and their responsibilities
4. **Delegate**: Launch worker sub-conversations via the Agent Canvas API
5. **Monitor**: Track progress of all workers periodically (set pauses to check status)
6. **Replan**: When workers finish, get stuck, or new info emerges - reassess and adapt
7. **Report**: Provide status updates to the user
8. **Coordinate**: Nudge stuck workers, answer questions, merge results

**Important: The Boss is a long-lived conversation** that should:
- Set a pause/sleep between status checks (e.g., 30-60 seconds)
- Check each worker's status via `GET /api/conversations/{id}`
- Check for errors or events that require intervention
- When a worker finishes, assess if work is complete or if re-planning needed
- When a worker is stuck (`stuck` status), try to nudge or reassign

### Worker Agents

- Each worker is a **normal conversation** accessible directly by the user
- Workers operate independently with their own workspace
- The user is **never locked out** — they can open any worker and interact directly
- The Boss is an **extra hand, not a gatekeeper**

## SDLC Workflow

The orchestrator follows this three-phase workflow:

### Phase 1: Decompose and Execute

```
To decompose a PRD and launch workers:

1. Parse the requirement source (text, file, or URL)
2. Identify distinct tasks that can run in parallel
3. For each task, create a worker conversation via POST /api/conversations
4. Track all conversation IDs and their responsibilities
```

### Phase 2: QA Validation

```
When workers complete their tasks:

1. Launch a QA worker to verify functionality
2. Take screenshots as necessary to prove functionality works
3. Document any issues found
4. Report back to the user
```

### Phase 3: Code Review

```
After QA passes:

1. Invoke the /code-review skill for each changed repository
2. Summarize findings for the user
3. Flag any blockers before merge
```

## Delegation API

### Finding the Session Key

```bash
# The correct environment variables for Agent Canvas:
# - AUTOMATION_LOCAL_API_KEY (for http://localhost:8000)
# - OH_SESSION_API_KEYS_0 (alternative key)
KEY="${AUTOMATION_LOCAL_API_KEY:-${OH_SESSION_API_KEYS_0:-}}"
if [ -z "$KEY" ] && [ -f "$HOME/.openhands/agent-canvas/api-key.txt" ]; then
  KEY="$(tr -d '\n' < "$HOME/.openhands/agent-canvas/api-key.txt")"
fi
```

### Delegate a Task

```bash
# Use the script: scripts/delegate.sh
./scripts/delegate.sh "Task description" "/path/to/workspace"
```

Or use the API directly (correct payload format):

```bash
BASE="${AGENT_CANVAS_BACKEND:-http://localhost:8000}"
KEY="${AUTOMATION_LOCAL_API_KEY:-${OH_SESSION_API_KEYS_0:-}}"
WORKDIR="${WORKDIR:-$HOME/workspace/delegated/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$WORKDIR"

# Fetch settings with encrypted secrets (X-Expose-Secrets: encrypted)
SETTINGS_JSON="$(curl -sS -H "X-Session-API-Key: $KEY" -H "X-Expose-Secrets: encrypted" "$BASE/api/settings")"
PROMPT='Complete task description with repo, branch, constraints, validation steps.'

PAYLOAD="$(jq -n --argjson settings "$SETTINGS_JSON" --arg prompt "$PROMPT" --arg workdir "$WORKDIR" '
  def base_agent_settings:
    ($settings.agent_settings // {}) | del(.schema_version) | del(.mcp_config);
  def with_tools:
    .tools = ((.tools // []) + [
      {name: "terminal", params: {}},
      {name: "file_editor", params: {}},
      {name: "task_tracker", params: {}},
      {name: "browser_tool_set", params: {}},
      {name: "canvas_ui", params: {}}
    ] | unique_by(.name));
  def with_skill_loading:
    .agent_context = ((.agent_context // {}) + {
      load_public_skills: true,
      load_user_skills: true,
      load_project_skills: true
    });
  ($settings.conversation_settings // {}) as $conv |
  {
    secrets_encrypted: true,
    agent_settings: (base_agent_settings | with_tools | with_skill_loading),
    tool_module_qualnames: {canvas_ui: "canvas_ui_tool"},
    workspace: {kind: "LocalWorkspace", working_dir: $workdir},
    confirmation_policy: {kind: "NeverConfirm"},
    max_iterations: (($conv.max_iterations // 1000) | if . == null then 1000 else . end),
    stuck_detection: true,
    autotitle: true,
    worktree: false,
    initial_message: {
      role: "user",
      content: [{type: "text", text: $prompt}],
      run: true
    }
  }
')"

curl -sS -X POST "$BASE/api/conversations" \
  -H "Content-Type: application/json" \
  -H "X-Session-API-Key: $KEY" \
  --data-binary "$PAYLOAD" | jq '{id, title, execution_status, workspace}'
```

### Monitor Workers

```bash
CID="<conversation_id>"
curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/$CID" \
  | jq '{id, title, execution_status, updated_at, agent_kind: .agent.kind}'

curl -sS -H "X-Session-API-Key: $KEY" \
  "$BASE/api/conversations/$CID/events/search?limit=20" \
  | jq '.events // .items // .'
```

### Status Values

- `idle` - Waiting for input
- `running` - Actively working
- `finished` - Completed successfully
- `error` - Failed with error
- `stuck` - Detected as stuck
- `stopped` - Manually stopped

## Boss Agent Commands

The user can instruct the Boss to:

| Command | Description |
|---------|-------------|
| `hire` | Start a new worker for additional work |
| `retire` | Close out a completed worker |
| `status` | Report on all active workers |
| `check <worker>` | Get detailed status of a specific worker |
| `talk <worker>` | Open direct communication with a worker |
| `nudge <worker>` | Send a reminder to a stuck worker |
| `report` | Summarize all work completed |

## Handling Requirement Sources

### Free Text
Parse the text directly to extract tasks.

### Markdown File
Read the file and extract tasks from headers, lists, or structured format.

### Jira/Linear URL
Fetch the ticket content via API and parse:
- For Linear: Use the GraphQL API with `LINEAR_API_KEY`
- Extract title, description, subtasks, priority

## Prompt Checklist for Workers

Include in each worker prompt:
- Repository owner/name and local path
- Branch, PR, issue, or ticket identifiers
- Current status and known blockers
- Exact files or subsystems in scope
- Dirty worktree warnings
- Whether to push, open PR, or only report
- Checks/tests to run
- Expected final report format

## Key Principles

1. **Transparency**: Always report worker status to the user
2. **Accessibility**: Users can directly access any worker conversation
3. **Self-Contained Prompts**: Workers know nothing from the orchestrator's context
4. **Independent Workspaces**: Each worker has its own isolated workspace
5. **Graceful Monitoring**: Check status regularly but don't overwhelm

## Additional Resources

### Reference Files
- **`references/delegation-patterns.md`** - Detailed delegation and monitoring patterns
- **`references/sdlc-workflow.md`** - Complete SDLC workflow documentation

### Helper Scripts
- **`scripts/delegate.sh`** - Create a new worker conversation
- **`scripts/monitor.sh`** - Monitor worker status and health
