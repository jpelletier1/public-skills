# Delegation Patterns

## Boss Agent Monitoring Loop

The Boss agent should run a monitoring loop to track worker progress:

```bash
#!/usr/bin/env bash
# Boss monitoring loop - run periodically to check worker status

BASE="http://localhost:8000"
KEY="${AUTOMATION_LOCAL_API_KEY}"
WORKERS=("worker-id-1" "worker-id-2" "worker-id-3")

check_worker() {
    local CID="$1"
    local INFO
    INFO="$(curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/$CID")"
    
    local STATUS TITLE ERROR
    STATUS="$(echo "$INFO" | jq -r '.execution_status')"
    TITLE="$(echo "$INFO" | jq -r '.title')"
    
    case "$STATUS" in
        running)   echo "🟢 $CID: running" ;;
        idle)      echo "🔵 $CID: idle (starting)" ;;
        finished)  echo "✅ $CID: finished" ;;
        error)     echo "❌ $CID: ERROR - check events" ;;
        stuck)     echo "⚠️  $CID: STUCK - needs intervention" ;;
        stopped)   echo "⏹️  $CID: stopped" ;;
        *)         echo "❓ $CID: unknown status: $STATUS" ;;
    esac
}

# Check all workers
for W in "${WORKERS[@]}"; do
    check_worker "$W"
done
```

## Event Monitoring for Errors

Check for ConversationErrorEvent that might require Boss intervention:

```bash
CID="<worker_id>"
curl -sS -H "X-Session-API-Key: $KEY" \
  "$BASE/api/conversations/$CID/events/search?limit=20" \
  | jq '[.items[]? | select(.kind == "ConversationErrorEvent") | {code, detail: (.detail[:200])}]'
```

Detailed patterns for effective multi-agent orchestration.

## Worker Creation Patterns

### Pattern 1: Task-Based Delegation

For each discrete task in a PRD:

```
1. Identify the task boundary (what can be done independently)
2. Create a worker with:
   - Clear task description
   - Repository and branch
   - Success criteria
   - Expected deliverables
```

### Pattern 2: Repository-Based Delegation

When multiple tasks target the same repository:

```
1. Group tasks by repository
2. Create one worker per repository
3. Include all related tasks in a single prompt
4. Prioritize tasks within the prompt
```

### Pattern 3: Parallel Execution

For independent tasks:

```
1. Launch all workers simultaneously
2. Monitor progress periodically
3. Collect results when all complete
4. Handle failures gracefully
```

## Monitoring Patterns

### Periodic Check-Ins

```bash
# Check every 5 minutes for long-running tasks
while true; do
  STATUS=$(curl -sS -H "X-Session-API-Key: $KEY" \
    "$BASE/api/conversations/$CID" | jq -r '.execution_status')
  
  if [ "$STATUS" = "finished" ]; then
    echo "Worker $CID completed!"
    break
  elif [ "$STATUS" = "error" ] || [ "$STATUS" = "stuck" ]; then
    echo "Worker $CID needs attention!"
    # Notify boss or handle automatically
  fi
  
  sleep 300  # 5 minutes
done
```

### Event-Based Monitoring

Subscribe to conversation events:

```bash
# Get latest events
curl -sS -H "X-Session-API-Key: $KEY" \
  "$BASE/api/conversations/$CID/events/search?limit=10" \
  | jq '.events[] | {type, created_at, content}'
```

## Communication Patterns

### Worker-to-Boss Reporting

Workers should report:
- Task completion status
- Files changed
- Tests run and results
- Blockers encountered
- Next steps

### Boss-to-Worker Instructions

The boss can send messages to workers:

```bash
# Send message to worker
curl -sS -X POST "$BASE/api/conversations/$CID/messages" \
  -H "Content-Type: application/json" \
  -H "X-Session-API-Key: $KEY" \
  -d '{"role": "user", "content": [{"type": "text", "text": "Please check..."}]}'
```

### User Direct Access

Users can always directly access workers:

```
UI:  http://localhost:8000/conversations/<worker_id>
API: http://localhost:8001/api/conversations/<worker_id>
```

## Error Handling Patterns

### Worker Failure

```bash
# Check worker status
STATUS=$(curl -sS -H "X-Session-API-Key: $KEY" \
  "$BASE/api/conversations/$CID" | jq -r '.execution_status')

if [ "$STATUS" = "error" ]; then
  # Get error details
  curl -sS -H "X-Session-API-Key: $KEY" \
    "$BASE/api/conversations/$CID" | jq '.last_error'
  
  # Options:
  # 1. Retry the worker
  # 2. Create a new worker with fixed prompt
  # 3. Report to user and ask for guidance
fi
```

### Stuck Detection

```bash
# Check if stuck
STATUS=$(curl -sS -H "X-Session-API-Key: $KEY" \
  "$BASE/api/conversations/$CID" | jq -r '.execution_status')

if [ "$STATUS" = "stuck" ]; then
  # Send nudge message
  curl -sS -X POST "$BASE/api/conversations/$CID/messages" \
    -H "Content-Type: application/json" \
    -H "X-Session-API-Key: $KEY" \
    -d '{"role": "user", "content": [{"type": "text", "text": "Please make progress or report blockers."}]}'
fi
```

## Cleanup Patterns

### Retiring a Worker

When a task is complete:

```bash
# Stop the conversation
curl -sS -X POST "$BASE/api/conversations/$CID/stop" \
  -H "X-Session-API-Key: $KEY"

# Optionally archive workspace
mv "$WORKDIR" "${WORKDIR}-archived-$(date +%Y%m%d)"
```

### Worker Tracking

Track workers in a JSON file:

```bash
# Create tracking file
TRACKING="$HOME/workspace/delegated/.worker-tracking.json"

# Add worker
echo '{"id": "'$CID'", "title": "'$TITLE'", "workdir": "'$WORKDIR'", "created": "'$(date -Iseconds)'"}' \
  | jq --argfile existing "$TRACKING" '($existing.conversations // []) + [inputs] | {conversations: .}' \
  > "${TRACKING}.tmp" && mv "${TRACKING}.tmp" "$TRACKING"
```

## Best Practices

1. **Self-contained prompts**: Workers know nothing from the boss context
2. **Clear success criteria**: Define what "done" means for each task
3. **Timeout handling**: Set max_iterations appropriately
4. **Regular status updates**: Keep the user informed
5. **Graceful degradation**: Handle failures without losing all progress
6. **Independent workspaces**: Each worker has its own directory
7. **Documentation**: Log decisions and rationale in prompts
