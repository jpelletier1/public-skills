#!/usr/bin/env bash
# monitor.sh - Monitor worker sub-conversation status
# Usage: ./monitor.sh [conversation_id] [-a|--all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BASE="${AGENT_CANVAS_BACKEND:-http://localhost:8000}"

# Find session key - use AUTOMATION_LOCAL_API_KEY for port 8000
KEY="${AUTOMATION_LOCAL_API_KEY:-${OH_SESSION_API_KEYS_0:-}}"
if [ -z "$KEY" ] && [ -f "$HOME/.openhands/agent-canvas/api-key.txt" ]; then
  KEY="$(tr -d '\n' < "$HOME/.openhands/agent-canvas/api-key.txt")"
fi

if [ -z "$KEY" ]; then
  echo "Error: No Agent Canvas session API key found" >&2
  exit 1
fi

show_status() {
  local CID="$1"
  local verbose="${2:-false}"
  
  local INFO
  INFO="$(curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/$CID")"
  
  local ID TITLE STATUS UPDATED MODEL
  ID="$(echo "$INFO" | jq -r '.id // "unknown"')"
  TITLE="$(echo "$INFO" | jq -r '.title // "Untitled"')"
  STATUS="$(echo "$INFO" | jq -r '.execution_status // "unknown"')"
  UPDATED="$(echo "$INFO" | jq -r '.updated_at // ""')"
  MODEL="$(echo "$INFO" | jq -r '.current_model_name // .current_model_id // "unknown"')"
  
  # Status emoji
  local EMOJI="⚪"
  case "$STATUS" in
    running) EMOJI="🟢" ;;
    idle) EMOJI="🔵" ;;
    finished) EMOJI="✅" ;;
    error) EMOJI="❌" ;;
    stuck) EMOJI="⚠️" ;;
    stopped) EMOJI="⏹️" ;;
  esac
  
  echo "$EMOJI $ID | $TITLE"
  echo "   Status: $STATUS | Model: $MODEL | Updated: $UPDATED"
  
  if [ "$verbose" = "true" ]; then
    echo "   UI:  http://localhost:8000/conversations/$ID"
    echo "   API: http://localhost:8001/api/conversations/$ID"
    
    # Get recent events
    local EVENTS
    EVENTS="$(curl -sS -H "X-Session-API-Key: $KEY" \
      "$BASE/api/conversations/$CID/events/search?limit=5")"
    
    local LAST_MSG
    LAST_MSG="$(echo "$EVENTS" | jq -r '[.events[], .items[]] | 
      map(select(.type == "message")) | 
      last // empty | 
      .content // "No messages"')"
    
    if [ "$LAST_MSG" != "No messages" ] && [ -n "$LAST_MSG" ]; then
      echo "   Last: ${LAST_MSG:0:100}..."
    fi
  fi
  echo ""
}

# Parse arguments
if [ "$#" -eq 0 ] || [ "$1" = "-a" ] || [ "$1" = "--all" ]; then
  # List all conversations
  echo "=== All Conversations ==="
  echo ""
  
  local CONVS
  CONVS="$(curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/search")"
  
  local IDS
  IDS="$(echo "$CONVS" | jq -r '[(.conversations[]?, .items[]?)] | 
    map(select(.execution_status | 
      IN("running", "idle", "stuck"))) | 
    .[].id')"
  
  if [ -z "$IDS" ] || [ "$IDS" = "null" ]; then
    echo "No active conversations found."
    exit 0
  fi
  
  while IFS= read -r CID; do
    [ -n "$CID" ] && show_status "$CID" "false"
  done <<< "$IDS"
  
elif [ "$1" = "-v" ] || [ "$1" = "--verbose" ]; then
  if [ -z "${2:-}" ]; then
    echo "Error: Conversation ID required for verbose mode" >&2
    exit 1
  fi
  show_status "$2" "true"
  
else
  # Single conversation
  show_status "$1" "false"
fi
