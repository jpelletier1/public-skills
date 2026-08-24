---
name: customer-feedback
description: This skill should be used when the user asks to "log customer feedback", "create a feedback ticket", "add feedback to Linear", "submit feedback", "/customer-feedback", or "record customer feedback". Creates a feedback ticket in Linear's Product team with Triage status and customer-feedback label. If a customer name is provided, attempts to associate the issue with a Customer Request for that customer.
---

# Customer Feedback Skill

Log customer feedback as a Linear issue in the Product team's Triage state with the customer-feedback label. When a customer name is detected in the context, also create or associate a Customer Request.

## When to Use

Activate this skill when the user requests to:
- "Log customer feedback"
- "Create a feedback ticket"
- "Add feedback to Linear"
- "Submit feedback"
- `/customer-feedback`
- "Record customer feedback"

## Prerequisites

**Check that LINEAR_API_KEY is set:**
```bash
[ -n "$LINEAR_API_KEY" ] && echo "LINEAR_API_KEY is set" || echo "LINEAR_API_KEY is NOT set"
```

If the API key is not set, ask the user to provide it before proceeding.

## Customer Detection

**Extract customer name from context.** If the user mentions a customer name (company name, person name, etc.) alongside the feedback, proceed to the Customer Association workflow.

Common indicators:
- "Customer: Acme Corp"
- "From: John at Acme"
- "Acme reported that..."
- "The customer [Name] wants..."

If no customer name is provided, skip the Customer Request section but still create the feedback issue.

## Workflow

### Step 1: Get the Product Team UUID

Query teams to find the "Product" team and get its UUID:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { teams { nodes { id name key } } }"
  }' | jq '.data.teams.nodes[] | select(.name == "Product")'
```

Save the `id` (UUID) value.

### Step 2: Get the Triage State UUID

Query workflow states to find the Triage state:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { workflowStates { nodes { id name type } } }"
  }' | jq '.data.workflowStates.nodes[] | select(.name == "Triage")'
```

Save the `id` value. If "Triage" doesn't exist, check available states:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { workflowStates { nodes { id name type } } }"
  }' | jq '.data.workflowStates.nodes'
```

### Step 3: Get or Create the customer-feedback Label

First, try to find an existing label:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { team(id: \"PRODUCT_TEAM_UUID\") { labels { nodes { id name } } } }"
  }' | jq '.data.team.labels.nodes[] | select(.name == "customer-feedback")'
```

If the label doesn't exist, create it:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation { labelCreate(input: { teamId: \"PRODUCT_TEAM_UUID\", name: \"customer-feedback\" }) { success label { id name } } }"
  }' | jq '.data.labelCreate.label'
```

Save the `id` (UUID) of the label.

### Step 4: Create the Feedback Issue

Use the team UUID, state UUID (Triage), and label UUID from previous steps:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation { issueCreate(input: { teamId: \"PRODUCT_TEAM_UUID\", title: \"FEEDBACK_TITLE\", description: \"FEEDBACK_DESCRIPTION\", stateId: \"TRIAGE_STATE_UUID\", labelIds: [\"CUSTOMER_FEEDBACK_LABEL_UUID\"] }) { success issue { id identifier title url } } }"
  }' | jq '.data.issueCreate'
```

**Required fields:**
- `title` — Concise summary of the feedback (from user's input)
- `description` — Structured feedback (see format below)
- `teamId` — Product team UUID
- `stateId` — Triage state UUID
- `labelIds` — Array containing the customer-feedback label UUID

**Optional fields to include if provided:**
- `priority` — 1 (Urgent), 2 (High), 3 (Medium), 4 (Low), or 0 (None)
- `assigneeId` — User UUID if assigning to someone specific

### Feedback Description Format

Structure the issue description with these sections:

```markdown
## Problem / Why it matters

[1-2 sentences on the underlying problem or business impact this addresses]

## Feedback

[Direct quotes, paraphrased feedback, or summary of what the customer reported]

## Example Scenario

[1-2 real-world scenarios where this problem occurs or the feature would be used]
```

**Guidelines:**
- **Problem / Why it matters**: Focus on root cause, not symptoms. Why does this matter to the business?
- **Feedback**: Use customer's own words when available. Include attribution if provided (e.g., "— Acme Corp, VP of Engineering")
- **Example Scenario**: Make it concrete. Who is affected, what are they trying to do, what goes wrong?

### Step 5: Confirm the Created Issue

Verify success and return the issue identifier and URL to the user.

### Step 6: Associate Customer (if customer name provided)

If a customer name was extracted from the context, proceed to associate with a Customer Request:

#### 6a: Search for Existing Customer

Search for customers matching the provided name:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { customers(first: 10, filter: { name: { containsInsensitive: \"CUSTOMER_NAME\" } }) { nodes { id name } } }"
  }' | jq '.data.customers.nodes'
```

Also try searching by variations of the name (acronym, partial match):

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { customers(first: 20) { nodes { id name } } }"
  }' | jq '.data.customers.nodes[] | select(.name | test(\"CUSTOMER_NAME\"; \"i\"))'
```

Save the matching customer's `id` (UUID). If no match found, proceed to create a new customer.

#### 6b: Create New Customer (if not found)

If no matching customer exists, create one:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation { customerCreate(input: { name: \"CUSTOMER_NAME\" }) { success customer { id name } } }"
  }' | jq '.data.customerCreate'
```

Save the new customer's `id`.

#### 6c: Create or Find Customer Request

Customer Requests link customers to issues. First, try to find an existing Customer Request for this customer:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { customerRequests(first: 10, filter: { customerId: { eq: \"CUSTOMER_UUID\" } }) { nodes { id customerId issueId state } } }"
  }' | jq '.data.customerRequests.nodes'
```

If no existing Customer Request found, create one and link to the feedback issue:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation { customerRequestCreate(input: { customerId: \"CUSTOMER_UUID\", issueId: \"FEEDBACK_ISSUE_UUID\" }) { success customerRequest { id customer { name } issue { identifier } } } }"
  }' | jq '.data.customerRequestCreate'
```

If the issue is not yet created at this point, note that the Customer Request should be created after the issue is confirmed.

## Example: Complete Feedback Ticket Creation (with Customer)

```bash
# 1. Get Product team UUID
TEAM_UUID=$(curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query": "query { teams { nodes { id name } } }"}' | jq -r '.data.teams.nodes[] | select(.name == "Product") | .id')

# 2. Get Triage state UUID
STATE_UUID=$(curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query": "query { workflowStates { nodes { id name type } } }"}' | jq -r '.data.workflowStates.nodes[] | select(.name == "Triage") | .id')

# 3. Get or create label
LABEL_UUID=$(curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d "{\"query\": \"query { team(id: \\\"$TEAM_UUID\\\") { labels { nodes { id name } } } }\"}" | jq -r '.data.team.labels.nodes[] | select(.name == "customer-feedback") // empty | .id')

# If label doesn't exist, create it
if [ -z "$LABEL_UUID" ]; then
  LABEL_UUID=$(curl -s -X POST https://api.linear.app/graphql \
    -H "Content-Type: application/json" \
    -H "Authorization: $LINEAR_API_KEY" \
    -d "{\"query\": \"mutation { labelCreate(input: { teamId: \\\"$TEAM_UUID\\\", name: \\\"customer-feedback\\\" }) { label { id } } }\"}" | jq -r '.data.labelCreate.label.id')
fi

# 4. Create the issue with structured feedback
DESCRIPTION="## Problem / Why it matters

Our customers need faster ways to onboard new team members without manual steps, which slows down adoption and increases support burden.

## Feedback

\"Onboarding a new engineer takes 2 hours of manual setup. We need this to be automatic.\" — Acme Corp, VP of Engineering

## Example Scenario

A team lead adds a new developer to the workspace. Instead of configuring permissions, integrations, and defaults manually, the system detects the new member and walks them through an automated setup flow that completes in under 5 minutes."

ISSUE_RESULT=$(curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d "{\"query\": \"mutation { issueCreate(input: { teamId: \\\"$TEAM_UUID\\\", title: \\\"Customer Feedback: Automated onboarding\\\", description: \\\"$DESCRIPTION\\\", stateId: \\\"$STATE_UUID\\\", labelIds: [\\\"$LABEL_UUID\\\"] }) { success issue { id identifier url } } }\"}" | jq '.data.issueCreate')

ISSUE_ID=$(echo "$ISSUE_RESULT" | jq -r '.issue.id')
ISSUE_IDENTIFIER=$(echo "$ISSUE_RESULT" | jq -r '.issue.identifier')

# 5. Search for customer (if customer name provided)
CUSTOMER_NAME="Acme Corp"
CUSTOMER_UUID=$(curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d "{\"query\": \"query { customers(first: 20) { nodes { id name } } }\"}" | jq -r ".data.customers.nodes[] | select(.name | test(\"$CUSTOMER_NAME\"; \"i\")) | .id")

# If customer doesn't exist, create it
if [ -z "$CUSTOMER_UUID" ]; then
  CUSTOMER_UUID=$(curl -s -X POST https://api.linear.app/graphql \
    -H "Content-Type: application/json" \
    -H "Authorization: $LINEAR_API_KEY" \
    -d "{\"query\": \"mutation { customerCreate(input: { name: \\\"$CUSTOMER_NAME\\\" }) { customer { id } } }\"}" | jq -r '.data.customerCreate.customer.id')
fi

# 6. Create Customer Request linking customer to issue
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d "{\"query\": \"mutation { customerRequestCreate(input: { customerId: \\\"$CUSTOMER_UUID\\\", issueId: \\\"$ISSUE_ID\\\" }) { success customerRequest { id } } }\"}" | jq '.data.customerRequestCreate'

echo "Created: $ISSUE_IDENTIFIER"
```

## User Input Collection

Before creating the issue, gather:
1. **Feedback title** — Brief summary (e.g., "Customer requests dark mode")
2. **Feedback details** — Full description from customer (quote, context, etc.)
3. **Priority** — If the user specifies urgency (default: 3 - Medium)
4. **Customer name** — If provided (will attempt to associate with Customer Request)

Ask the user for any missing required information before executing the API calls.

## Customer Association Notes

- **Partial matches**: When searching for customers, try partial name matches (e.g., "Acme" matches "Acme Corp")
- **Create if not found**: If no matching customer exists, create a new one using the provided name
- **Customer Request linking**: The Customer Request ties the customer record to the Linear issue, enabling customer-centric views
- **Confirmation**: Always confirm both the issue and customer association to the user
