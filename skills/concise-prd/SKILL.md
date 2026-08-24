---
name: concise-prd
description: This skill should be used when the user asks to "create a lightweight PRD", "write a concise PRD", "generate a product requirements document", "/concise-prd", or "make a PRD". Creates a minimal, focused PRD with user problem, scenarios, acceptance criteria, and why it matters.
---

# Concise PRD Skill

Generate lightweight, focused Product Requirements Documents (PRDs) that capture essential information without unnecessary overhead.

## When to Use

Activate this skill when the user requests a PRD in any of these forms:
- "Create a lightweight PRD for..."
- "Write a concise PRD"
- "/concise-prd"
- "Generate a PRD"
- "Make a product requirements document"

## PRD Template Structure

Output a PRD with the following sections:

### User Problem

1-3 sentences describing the core problem or need from the user's perspective. Focus on the pain point, not the solution.

**Format:**
```
### User Problem

[Clear statement of the problem in 1-3 sentences]
```

### Scenarios

Bullet-point list of real-world scenarios where this problem occurs or the feature would be used.

**Format:**
```
### Scenarios

- [Scenario 1]
- [Scenario 2]
- [Scenario 3]
```

### I Can Statements

Acceptance criteria written from the user's perspective as "I can..." statements. These define when the feature is complete.

**Format:**
```
### I Can...

- I can [specific capability 1]
- I can [specific capability 2]
- I can [specific capability 3]
```

### Why It Matters

1-3 bullets explaining the importance and business value. Focus on outcomes, efficiency gains, or user impact.

**Format:**
```
### Why It Matters

- [Impact statement 1]
- [Impact statement 2]
- [Impact statement 3, if applicable]
```

### Customer Evidence

Include only if the user provided customer quotes, data, or feedback. If not provided, note "None provided."

**Format:**
```
### Customer Evidence

[Customer quotes, data, or research findings, OR "None provided."]
```

## Generation Guidelines

1. **Extract from context**: Use the provided conversation context, user description, or any additional details given.

2. **Be specific**: Avoid vague language. Each section should be concrete and actionable.

3. **User-centric**: Frame problem and acceptance criteria from the user's viewpoint, not technical implementation.

4. **Prioritize brevity**: A concise PRD is valuable precisely because it's quick to read and act upon. Avoid adding sections not requested.

5. **Ask for clarification if needed**: If critical information is missing for any section, ask the user before inventing details.

## Example Output

```
### User Problem

Users need a way to quickly share meeting notes with attendees without manually drafting emails, leading to delays and inconsistent follow-ups.

### Scenarios

- A project manager wraps up a standup and immediately shares key decisions
- A sales rep finishes a client call and sends highlights to the team
- A team lead documents decisions made in a 1:1 and shares action items

### I Can...

- I can share notes with one click to all meeting attendees
- I can review and edit notes before sending
- I can track when attendees have viewed the shared notes

### Why It Matters

- Reduces manual work for meeting organizers by automating distribution
- Ensures consistent communication across the organization
- Improves team alignment and reduces follow-up delays

### Customer Evidence

"Meeting follow-up used to take 15 minutes. Now it's instant." — Beta user feedback
```

## Quick Reference

| Section | Length | Focus |
|---------|--------|-------|
| User Problem | 1-3 sentences | Pain point |
| Scenarios | 3-5 bullets | Real-world use |
| I Can Statements | 3-5 bullets | Acceptance criteria |
| Why It Matters | 1-3 bullets | Business value |
| Customer Evidence | Conditional | Quotes/data if provided |
