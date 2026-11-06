#!/usr/bin/env python3
"""Deterministic helpers for the linear-github-sync skill.

Subcommands:
  links             List OpenHands/enterprise issues attached to a Linear issue and
                    whether Linear's native GitHub sync owns each one.
  conversation-url  Print the URL of the current OpenHands conversation.
  check-leaks       Fail if a draft contains a denied term, email, or private link.
  create            Create a GitHub issue from an anonymized draft (v1), then link it
                    to the Linear ticket and verify the link.
  link              Link an existing OpenHands/enterprise issue to a Linear ticket
                    and verify it (retry after a failed link in `create`).
  update            Rewrite a GitHub issue body from an anonymized draft (vN+1).

`create` and `update` print the exact final body with --dry-run; run the same
command without --dry-run after approval so the posted text matches the draft.
Stdlib only.
"""

import argparse
import datetime
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

REPO = "OpenHands/enterprise"
GITHUB_API = "https://api.github.com"
LINEAR_API = "https://api.linear.app/graphql"
MARKER = "<!-- linear-feedback-sync -->"
HISTORY_RE = re.compile(r"^- v(\d+) · ", re.MULTILINE)
ISSUE_URL_RE = re.compile(
    r"^https://github\.com/OpenHands/enterprise/issues/(\d+)(?:[/#?].*)?$", re.IGNORECASE
)
AI_NOTE = "_Synced from Linear by an AI agent (OpenHands)._"

PRIVATE_LINK_PATTERNS = {
    "Linear link": r"linear\.app/",
    "HappyFox link": r"happyfox|support\.openhands\.dev",
    "Slack link": r"slack\.com/",
    "Notion link": r"notion\.so/|notion\.site/",
    "Google Docs link": r"docs\.google\.com/|drive\.google\.com/",
    "Granola link": r"granola\.ai/",
}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
ALLOWED_EMAIL_DOMAINS = {"openhands.dev", "all-hands.dev", "users.noreply.github.com"}


def http_json(url, headers, data=None, method="GET", max_attempts=5):
    payload = json.dumps(data).encode() if data is not None else None
    for attempt in range(max_attempts):
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            h = {k.lower(): v for k, v in e.headers.items()}
            limited = e.code == 429 or (e.code == 403 and h.get("x-ratelimit-remaining") == "0")
            if not limited or attempt == max_attempts - 1:
                sys.exit(f"HTTP {e.code} from {method} {url}: {e.read().decode()[:500]}")
            if h.get("retry-after"):
                wait = float(h["retry-after"]) + 0.5
            elif h.get("x-ratelimit-reset"):
                wait = max(0.0, float(h["x-ratelimit-reset"]) - time.time()) + 1.0
            else:
                wait = 2.0 * (2**attempt) + random.uniform(0, 1)
            print(f"[rate limit] retrying in {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)


def gh(path, data=None, method="GET"):
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    return http_json(f"{GITHUB_API}{path}", headers, data, method)


def linear(query, variables):
    key = os.environ.get("LINEAR_API_KEY") or sys.exit(
        "LINEAR_API_KEY is not set; use the Linear MCP fallback in SKILL.md"
    )
    headers = {"Authorization": key, "Content-Type": "application/json"}
    res = http_json(LINEAR_API, headers, {"query": query, "variables": variables}, "POST")
    if res.get("errors"):
        sys.exit(f"Linear error: {res['errors']}")
    return res["data"]


def cmd_links(args):
    data = linear(
        "query($id: String!) { issue(id: $id) { identifier attachments { nodes "
        "{ url title sourceType } } } }",
        {"id": args.linear_id},
    )
    links = []
    for a in data["issue"]["attachments"]["nodes"]:
        m = ISSUE_URL_RE.match(a["url"])
        if m:
            links.append({
                "number": int(m.group(1)),
                "url": a["url"],
                "title": a["title"],
                "source_type": a["sourceType"],
                "natively_synced": a["sourceType"] == "github",
            })
    print(json.dumps({"linear_id": data["issue"]["identifier"], "enterprise_issues": links}, indent=2))


def cmd_conversation_url(args):
    path = os.environ.get("OH_CONVERSATIONS_PATH") or sys.exit("OH_CONVERSATIONS_PATH is not set")
    ids = [d for d in os.listdir(path) if re.fullmatch(r"[0-9a-f]{32}", d)]
    if len(ids) != 1:
        sys.exit(f"Expected one conversation directory in {path}, found {len(ids)}: {ids}")
    print(f"{args.host.rstrip('/')}/conversations/{ids[0]}")


def find_leaks(text, terms):
    hits = []
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE):
            hits.append(f"denied term: {term!r}")
    for label, pattern in PRIVATE_LINK_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(label)
    for m in EMAIL_RE.finditer(text):
        if m.group(1).lower() not in ALLOWED_EMAIL_DOMAINS:
            hits.append(f"email address: {m.group(0)}")
    return hits


def load_terms(path):
    with open(path) as f:
        return [t.strip() for t in f if t.strip() and not t.startswith("#")]


def assert_clean(title, content, terms_file):
    hits = find_leaks(f"{title}\n{content}", load_terms(terms_file))
    if hits:
        sys.exit("Refusing to continue; the draft still contains:\n  - " + "\n  - ".join(hits))


def cmd_check_leaks(args):
    with open(args.content_file) as f:
        assert_clean(args.title or "", f.read(), args.deny_terms)
    print("clean")


def split_body(body):
    body = body or ""
    idx = body.find(MARKER)
    if idx == -1:
        return body.rstrip(), []
    history = [ln for ln in body[idx:].splitlines() if HISTORY_RE.match(ln)]
    return body[:idx].rstrip().removesuffix("---").rstrip(), history


def render(content, history, version, verb, linear_id):
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    history = history + [f"- v{version} · {today} · {verb} from Linear {linear_id}"]
    return (
        f"{content.rstrip()}\n\n---\n{MARKER}\n#### Sync history\n{AI_NOTE}\n\n"
        + "\n".join(history)
        + "\n"
    ), today


def read_content(path):
    with open(path) as f:
        content = f.read()
    if MARKER in content:
        sys.exit("The draft must not contain the sync-history block; the script adds it")
    return content


def cmd_create(args):
    content = read_content(args.content_file)
    assert_clean(args.title, content, args.deny_terms)
    body, _ = render(content, [], 1, "Created", args.linear_id)
    if args.dry_run:
        print(f"TITLE: {args.title}\nLABELS: {', '.join(args.label)}\n\n{body}")
        return
    issue = gh(f"/repos/{REPO}/issues", {"title": args.title, "body": body, "labels": args.label}, "POST")
    result = {"number": issue["number"], "url": issue["html_url"], "version": 1}
    # The GitHub issue already exists, so a linking failure must still report its number.
    try:
        link_linear(args.linear_id, issue["html_url"], issue["number"])
        result["linear_linked"] = True
    except SystemExit as e:
        result["linear_linked"] = False
        result["linear_link_error"] = str(e.code)
    print(json.dumps(result))
    if not result["linear_linked"]:
        sys.exit(1)


def link_linear(linear_id, url, number):
    """Attach the GitHub issue to the Linear ticket as a plain link and verify it.

    Uses attachmentCreate rather than the GitHub integration so Linear's native
    two-way sync does not take ownership of the issue body.
    """
    issue_id = linear("query($id: String!) { issue(id: $id) { id } }", {"id": linear_id})["issue"]["id"]
    res = linear(
        "mutation($input: AttachmentCreateInput!) { attachmentCreate(input: $input) "
        "{ success attachment { url } } }",
        {"input": {"issueId": issue_id, "url": url, "title": f"{REPO}#{number}"}},
    )["attachmentCreate"]
    if not res["success"]:
        sys.exit(f"attachmentCreate did not succeed for {linear_id}")
    nodes = linear(
        "query($id: String!) { issue(id: $id) { attachments { nodes { url sourceType } } } }",
        {"id": linear_id},
    )["issue"]["attachments"]["nodes"]
    match = [a for a in nodes if (m := ISSUE_URL_RE.match(a["url"])) and int(m.group(1)) == number]
    if not match:
        sys.exit(f"{url} is not attached to {linear_id} after attachmentCreate")
    if any(a["sourceType"] == "github" for a in match):
        sys.exit(f"{url} was attached to {linear_id} as a native GitHub sync; replace it with a plain link")


def cmd_link(args):
    m = ISSUE_URL_RE.match(args.url) or sys.exit(f"Not an {REPO} issue URL: {args.url}")
    link_linear(args.linear_id, args.url, int(m.group(1)))
    print(json.dumps({"linear_id": args.linear_id, "url": args.url, "linear_linked": True}))


def cmd_update(args):
    content = read_content(args.content_file)
    current = gh(f"/repos/{REPO}/issues/{args.issue}")
    title = args.title or current["title"]
    assert_clean(title, content, args.deny_terms)
    _, history = split_body(current["body"])
    version = max((int(HISTORY_RE.match(h).group(1)) for h in history), default=0) + 1
    body, today = render(content, history, version, "Updated", args.linear_id)
    if args.dry_run:
        print(f"ISSUE: {current['html_url']}\nTITLE: {title}\nVERSION: v{version}\n\n{body}")
        return
    patch = {"body": body}
    if args.title:
        patch["title"] = args.title
    gh(f"/repos/{REPO}/issues/{args.issue}", patch, "PATCH")
    gh(
        f"/repos/{REPO}/issues/{args.issue}/comments",
        {"body": f"Issue description updated to **v{version}** ({today}) from Linear {args.linear_id}.\n\n"
                 "_Posted by an AI agent (OpenHands)._"},
        "POST",
    )
    print(json.dumps({"number": args.issue, "url": current["html_url"], "version": version}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("links")
    s.add_argument("linear_id")
    s.set_defaults(func=cmd_links)

    s = sub.add_parser("conversation-url")
    s.add_argument("--host", required=True, help="OpenHands app URL, e.g. https://app.all-hands.dev")
    s.set_defaults(func=cmd_conversation_url)

    s = sub.add_parser("link")
    s.add_argument("--linear-id", required=True)
    s.add_argument("--url", required=True, help="https://github.com/OpenHands/enterprise/issues/<N>")
    s.set_defaults(func=cmd_link)

    s = sub.add_parser("check-leaks")
    s.add_argument("--content-file", required=True)
    s.add_argument("--title")
    s.add_argument("--deny-terms", required=True)
    s.set_defaults(func=cmd_check_leaks)

    for name, func in (("create", cmd_create), ("update", cmd_update)):
        s = sub.add_parser(name)
        s.add_argument("--linear-id", required=True)
        s.add_argument("--content-file", required=True, help="Anonymized markdown body, no history block")
        s.add_argument("--deny-terms", required=True, help="File of real names to block, one per line")
        s.add_argument("--dry-run", action="store_true")
        if name == "create":
            s.add_argument("--title", required=True)
            s.add_argument("--label", action="append", required=True, choices=["bug", "enhancement"])
        else:
            s.add_argument("--issue", type=int, required=True)
            s.add_argument("--title", help="Replace the GitHub title (anonymized)")
        s.set_defaults(func=func)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
