# SDLC Workflow Reference

Complete software development lifecycle workflow for multi-agent orchestration.

## Overview

The orchestrator follows a three-phase SDLC:

```
Phase 1: Decompose & Execute    → Launch workers, parallel development
Phase 2: QA Validation          → Verify functionality, capture evidence
Phase 3: Code Review            → Review changes, ensure quality
```

## Phase 1: Decompose & Execute

### Step 1.1: Parse Requirements

Accept requirements from multiple sources:

| Source | Parsing Method |
|--------|----------------|
| Free text | Direct extraction of tasks |
| Markdown file | Read file, parse headers/lists |
| Jira URL | Fetch via REST API |
| Linear URL | Fetch via GraphQL API |

### Step 1.2: Decompose into Tasks

Break down the PRD into atomic tasks:

```
To decompose requirements:

1. Identify core features (must-have vs nice-to-have)
2. Identify dependencies (what must happen first)
3. Identify parallelizable work (what can happen simultaneously)
4. Assign task priority based on dependencies
5. Define acceptance criteria for each task
```

### Step 1.3: Launch Workers

For each task or group of related tasks:

```bash
# Example: Launching workers for a feature implementation
WORKER_1=$(./delegate.sh "Implement user authentication module..." "/path/to/repo1")
WORKER_2=$(./delegate.sh "Create database schema for orders..." "/path/to/repo2")
WORKER_3=$(./delegate.sh "Build payment integration..." "/path/to/repo3")
```

### Step 1.4: Monitor Progress

Track worker status:

```bash
# Check all workers periodically
for CID in $WORKER_1 $WORKER_2 $WORKER_3; do
  ./monitor.sh "$CID"
done
```

### Step 1.5: Coordinate

Handle inter-worker dependencies if needed:

```
When workers need to coordinate:

1. Boss acts as communication intermediary
2. Share outputs from one worker as input to another
3. Ensure proper sequencing when needed
```

## Phase 2: QA Validation

### Step 2.1: Launch QA Worker

When development workers complete:

```bash
./delegate.sh "QA Task:
1. Review changes in repository
2. Run test suite: npm test / pytest / cargo test
3. Verify functionality matches acceptance criteria
4. Take screenshots proving key features work
5. Report any bugs found

Expected output:
- Test results summary
- Screenshot evidence of functionality
- List of any issues found
" "/path/to/qa-workspace"
```

### Step 2.2: Automated Testing

QA worker should run:

```
- Unit tests
- Integration tests  
- E2E tests if applicable
- Lint/format checks
- Security scans
```

### Step 2.3: Screenshot Evidence

For UI features:

```
To capture screenshots:

1. Launch the application
2. Navigate to relevant screens
3. Use browser tool to capture screenshots
4. Save to evidence directory
5. Include in final report
```

### Step 2.4: QA Report

QA worker reports:

```
QA Report Template:

## Test Summary
- Tests passed: X/Y
- Bugs found: N

## Evidence
[Screenshots of key functionality]

## Issues
- Issue 1: Description, severity, reproduction steps
- Issue 2: ...

## Recommendation
- [ ] Ready for merge
- [ ] Needs fixes before merge
```

## Phase 3: Code Review

### Step 3.1: Invoke Code Review Skill

Use the `/code-review` skill for each changed repository:

```
To invoke code review:

1. Load the code-review skill
2. Point to the changed repository
3. Specify the branch/PR to review
4. Collect findings
```

### Step 3.2: Code Review Scope

The code review should cover:

```
- Code quality and style
- Security vulnerabilities
- Performance concerns
- Best practices adherence
- Test coverage
- Documentation completeness
```

### Step 3.3: Review Findings

Collect and summarize findings:

```
Code Review Summary:

## Repository: example-repo

### Issues by Severity

**Blocker:**
- Issue 1: SQL injection vulnerability in user input

**Major:**
- Issue 2: Missing error handling in payment processing

**Minor:**
- Issue 3: Inconsistent naming convention

### Recommendations
- Fix blocker before merge
- Consider refactoring X for better maintainability

### Approval Status
[ ] Approved
[ ] Changes requested
[ ] Blocked
```

## Integration: End-to-End Flow

```
User Request
    │
    ▼
┌─────────────────────────┐
│   Boss: Parse PRD        │
│   - Extract tasks        │
│   - Identify workers     │
└────────────┬────────────┘
             │
             ▼
    ┌────────────────┐
    │ Worker 1       │◄─── Task A
    ├────────────────┤
    │ Worker 2       │◄─── Task B (parallel)
    ├────────────────┤
    │ Worker N       │◄─── Task N
    └───────┬────────┘
            │
            ▼
    ┌────────────────┐
    │ Boss: Monitor  │
    │ - Track status │
    │ - Handle issues│
    └───────┬────────┘
            │
            ▼ (all complete)
    ┌────────────────┐
    │ QA Worker      │
    │ - Test changes │
    │ - Screenshots  │
    └───────┬────────┘
            │
            ▼
    ┌────────────────┐
    │ Code Review    │
    │ /code-review   │
    └───────┬────────┘
            │
            ▼
      Final Report
```

## Boss Agent Commands Reference

| Command | Action |
|---------|--------|
| `hire <task>` | Start a new worker |
| `retire <worker>` | Close completed worker |
| `status` | Report on all workers |
| `check <worker>` | Detailed worker status |
| `talk <worker> <message>` | Send message to worker |
| `nudge <worker>` | Remind stuck worker |
| `report` | Summarize all work |

## Error Recovery

### Development Worker Fails

```
Options:
1. Retry: Re-launch with same prompt
2. Fix: Modify prompt based on error and retry
3. Redistribute: Assign to different worker
4. Escalate: Report to user with error details
```

### QA Finds Issues

```
Flow:
1. QA reports issues
2. Boss categorizes severity
3. For minor: Document and continue
4. For major/blocker: 
   - Create new worker for fix
   - Or assign back to original worker
5. Re-run QA after fixes
```

### Code Review Blocks

```
Flow:
1. Reviewer flags blocking issues
2. Boss creates fix task
3. Developer addresses issues
4. Re-review or proceed with documented risks
```
