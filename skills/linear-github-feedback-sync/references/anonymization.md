# Anonymization rules

`OpenHands/enterprise` is a **public** repository. Treat every word that reaches it as
published. Anonymize the title and the body before showing the draft to the user.

## What to replace

| Found in the Linear ticket | Replace with |
|---|---|
| Customer or prospect company name, including abbreviations, product nicknames, and possessives ("Acme's") | `AlphaCo`, `BetaCo`, `GammaCo`, `DeltaCo`, `EpsilonCo`, ... in order of first appearance |
| A person at a customer (name, handle, title + name) | Their role: "a customer platform engineer", "AlphaCo's admin" |
| A person at OpenHands | Remove the name. Use the role ("the support engineer") or drop the sentence |
| Customer email address or email domain | Remove. Use "a customer email address" if context needs it |
| Customer hostnames, cluster names, tenant/org IDs, bucket names, internal URLs | `alphaco.example.com`, `<customer-cluster>`, `<org-id>` |
| Links to Linear, HappyFox, Slack, Notion, Google Docs, Granola, Gong | Remove the link. Keep a neutral summary of what it showed, if useful |
| Contract values, seat counts, renewal dates, deal stage, revenue | Remove |
| Screenshots or attachments from the Linear ticket | Do not copy. Describe what matters in text |

Keep: OpenHands product names, public open-source projects, cloud providers
(AWS, GCP, Azure), public tools (Okta, GitLab, Bitbucket), version numbers, error
messages with customer details removed, and the Linear identifier (`PRD-123`).

## Where names hide

Check every one of these, not only the description:

- The Linear title. The URL slug includes it, so never post the Linear URL.
- Linear **Customers** linked to the ticket (Customer Requests) and the workspace
  Customers list (`list_customers` in the Linear MCP).
- Project names, labels, and team names on the ticket ("[Acme] SSO pilot").
- Quoted Slack messages, email signatures, log lines, stack traces, file paths
  (`/home/jdoe/...`), and code blocks.
- Image alt text and link text.

## Alias mapping

- Build a fresh mapping per ticket. Use the same alias for the same company
  everywhere in that ticket's title and body.
- Do not write the mapping to GitHub or to Linear. Show it to the user in the
  conversation only, next to the draft, so they can check it.
- When updating an existing GitHub issue, read its current body and reuse aliases
  that already refer to the same company in the same role, if the match is
  obvious. Otherwise, assign fresh aliases.

## Deny-terms file

Write every real name, domain, and identifier that was replaced to a temp file,
one per line, for example `/tmp/feedback-sync/PRD-123.deny`:

```
Acme
Acme Corp
acme.io
Jane Doe
jdoe
```

Include the full Linear Customers list too, so a name that was missed in review
still blocks the write. Pass this file as `--deny-terms`. The script refuses to
create or update an issue while any term, a non-OpenHands email address, or a
private-tool link remains. If it refuses, fix the draft; never shorten the file to
get past the check.

Delete the temp directory when the run ends.
