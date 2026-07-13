#!/usr/bin/env bash
# delegate.sh - Create a new worker sub-conversation
# Usage: ./delegate.sh "Task description" [workspace_path]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load configuration from environment or defaults
BASE="${AGENT_CANVAS_BACKEND:-http://localhost:8000}"
PROMPT="${1:-}"
WORKDIR_ARG="${2:-}"

# Find session key - use AUTOMATION_LOCAL_API_KEY for port 8000
KEY="${AUTOMATION_LOCAL_API_KEY:-${OH_SESSION_API_KEYS_0:-}}"
if [ -z "$KEY" ] && [ -f "$HOME/.openhands/agent-canvas/api-key.txt" ]; then
  KEY="$(tr -d '\n' < "$HOME/.openhands/agent-canvas/api-key.txt")"
fi

if [ -z "$KEY" ]; then
  echo "Error: No Agent Canvas session API key found" >&2
  echo "Set AUTOMATION_LOCAL_API_KEY or OH_SESSION_API_KEYS_0" >&2
  exit 1
fi

if [ -z "$PROMPT" ]; then
  echo "Usage: $0 <task_description> [workspace_path]" >&2
  echo "  task_description: The work to be done by the worker" >&2
  echo "  workspace_path:   Optional workspace directory (default: auto-generated)" >&2
  exit 1
fi

# Generate workspace if not provided
if [ -z "$WORKDIR_ARG" ]; then
  WORKDIR="$HOME/workspace/delegated/$(date +%Y%m%d-%H%M%S)-$$"
else
  WORKDIR="$WORKDIR_ARG"
fi
mkdir -p "$WORKDIR"

# Fetch current agent settings with encrypted secrets
SETTINGS_JSON="$(curl -sS -H "X-Session-API-Key: $KEY" -H "X-Expose-Secrets: encrypted" "$BASE/api/settings")"

# Build the payload using jq - with secrets_encrypted: true for proper LLM auth
PAYLOAD="$(jq -n \
  --argjson settings "$SETTINGS_JSON" \
  --arg prompt "$PROMPT" \
  --arg workdir "$WORKDIR" '
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

# Create the conversation
RESPONSE="$(curl -sS -X POST "$BASE/api/conversations" \
  -H "Content-Type: application/json" \
  -H "X-Session-API-Key: $KEY" \
  --data-binary "$PAYLOAD")"

# Extract and display results
CONV_ID="$(echo "$RESPONSE" | jq -r '.id // empty')"
TITLE="$(echo "$RESPONSE" | jq -r '.title // "Untitled"')"
STATUS="$(echo "$RESPONSE" | jq -r '.execution_status // "unknown"')"

if [ -z "$CONV_ID" ]; then
  echo "Error: Failed to create conversation" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

echo "Worker conversation created successfully!"
echo ""
echo "  Conversation ID: $CONV_ID"
echo "  Title:           $TITLE"
echo "  Status:          $STATUS"
echo "  Workspace:       $WORKDIR"
echo ""
echo "  UI:  http://localhost:8000/conversations/$CONV_ID"
echo "  API: http://localhost:8001/api/conversations/$CONV_ID"
echo ""

# Optionally save to tracking file
TRACKING_FILE="${WORKDIR%/*}/.worker-tracking.json"
if [ -f "$TRACKING_FILE" ]; then
  # Add to existing tracking
  TEMP=$(mktemp)
  jq --arg id "$CONV_ID" --arg title "$TITLE" --arg workdir "$WORKDIR" \
     'map(select(.id == $id)) + [{id: $id, title: $title, workdir: $workdir, created: now}] 
     | unique_by(.id)' \
     "$TRACKING_FILE" > "$TEMP" && mv "$TEMP" "$TRACKING_FILE" 2>/dev/null || true
fi

echo "$CONV_ID"
