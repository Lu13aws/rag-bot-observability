"""Create the Scrum backlog (labels, milestones, issues, sub-issues, project
fields) from tools/backlog/backlog.json using the GitHub CLI.

- Idempotent: existing labels, milestones and issues (matched by title) are
  skipped; sub-issue links and project fields are only set if missing/different.
- --dry-run: only read from GitHub and print the planned actions.
- Content check: aborts before any action if an issue text contains an
  account ID, ARN, access key, the project bucket name or platform internals.

Usage:
    python tools/create_backlog.py --dry-run
    python tools/create_backlog.py
    python tools/create_backlog.py --dry-run --show-body S2.2.4
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "tools" / "backlog" / "backlog.json"
CONFIG = ROOT / "infra" / "config.env"

FORBIDDEN = [
    (r"\b\d{12}\b", "12-digit number (account ID?)"),
    (r"arn:aws:", "ARN"),
    (r"\b(AKIA|ASIA)[0-9A-Z]{16}\b", "access key"),
    (r"ai-platform|ai-consulting|nat gateway|\brds\b|lambda", "platform internals"),
]


# --- helpers -----------------------------------------------------------------

TRANSIENT = re.compile(r"\b50[0234]\b|no healthy upstream|timeout|connection reset", re.IGNORECASE)


def gh(*args: str, input_text: str | None = None, check: bool = True) -> str:
    """Run gh; retry up to 4 times with backoff on transient server errors."""
    for attempt in range(5):
        result = subprocess.run(
            ["gh", *args], input=input_text, capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode == 0 or not TRANSIENT.search(result.stderr):
            break
        wait = 5 * 2 ** attempt
        print(f"    transient error, retry in {wait}s: {result.stderr.strip()[:80]}")
        time.sleep(wait)
    if check and result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def gh_json(*args: str):
    out = gh(*args)
    return json.loads(out) if out.strip() else None


def bucket_name() -> str | None:
    if not CONFIG.exists():
        return None
    for line in CONFIG.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("BUCKET="):
            return line.split("=", 1)[1].strip() or None
    return None


# --- issue bodies --------------------------------------------------------------

def build_body(item: dict, by_id: dict) -> str:
    parts = []
    if item.get("description"):
        parts.append(f"## Goal\n{item['description']}")
    if item.get("story"):
        parts.append(f"## User story\n{item['story']}")
    if item.get("acceptance"):
        lines = [f"- [{'x' if done else ' '}] {text}" for text, done in item["acceptance"]]
        parts.append("## Acceptance criteria\n" + "\n".join(lines))
    if item.get("refs"):
        parts.append("## References\n" + ", ".join(f"`{r}`" for r in item["refs"]))
    if item.get("parent"):
        parts.append(f"## Parent\n{by_id[item['parent']]['title']}")
    if item.get("completed"):
        c = item["completed"]
        parts.append(f"## Completion\nCompleted on {c['date']} (commit `{c['commit']}`).")
    return "\n\n".join(parts) + "\n"


def content_check(items: list[dict], by_id: dict) -> list[str]:
    patterns = list(FORBIDDEN)
    bucket = bucket_name()
    if bucket:
        patterns.append((re.escape(bucket), "project bucket name"))
    problems = []
    for item in items:
        text = item["title"] + "\n" + build_body(item, by_id)
        for pattern, label in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                problems.append(f"{item['id']}: contains {label}")
    return problems


# --- main ----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show-body", metavar="ID", help="print the body of one issue")
    args = parser.parse_args()
    dry = args.dry_run

    backlog = json.loads(BACKLOG.read_text(encoding="utf-8"))
    items = backlog["issues"]
    by_id = {i["id"]: i for i in items}

    problems = content_check(items, by_id)
    if problems:
        print("Content check FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print(f"Content check passed ({len(items)} issues).")

    if args.show_body:
        print(f"\n--- {by_id[args.show_body]['title']}\n{build_body(by_id[args.show_body], by_id)}")
        return

    repo = gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    owner = repo.split("/")[0]
    mode = "DRY RUN" if dry else "APPLY"
    print(f"Repository: {repo}  ({mode})\n")

    # 1. Labels
    existing_labels = {l["name"] for l in gh_json("label", "list", "--limit", "200", "--json", "name")}
    print("== Labels")
    for label in backlog["labels"]:
        if label["name"] in existing_labels:
            print(f"  skip    {label['name']}")
            continue
        print(f"  create  {label['name']} (#{label['color']})")
        if not dry:
            gh("label", "create", label["name"], "--color", label["color"],
               "--description", label["description"])

    # 2. Milestones
    existing_ms = {m["title"]: m for m in gh_json("api", f"repos/{repo}/milestones?state=all&per_page=100")}
    print("\n== Milestones")
    for ms in backlog["milestones"]:
        if ms["title"] in existing_ms:
            print(f"  skip    {ms['title']}")
            continue
        # Created open: gh issue create only finds open milestones. Closed at the end.
        print(f"  create  {ms['title']} due {ms['due_on']} (open, target state: {ms['state']})")
        if not dry:
            created = gh_json("api", f"repos/{repo}/milestones", "-X", "POST",
                              "-f", f"title={ms['title']}", "-f", f"due_on={ms['due_on']}T12:00:00Z",
                              "-f", f"description={ms['description']}", "-f", "state=open")
            existing_ms[ms["title"]] = created

    # 3. Issues (matched by title)
    existing = {i["title"]: i for i in gh_json(
        "issue", "list", "--state", "all", "--limit", "500", "--json", "number,title,state,url")}
    print("\n== Issues")
    numbers: dict[str, int] = {}
    for item in items:
        meta = f"[{','.join(item['labels'])}] {item.get('milestone') or '-'} | {item['status']}" \
               f"{' | ' + item['priority'] if item.get('priority') else ''}{' | closed' if item.get('closed') else ''}"
        if item["title"] in existing:
            numbers[item["id"]] = existing[item["title"]]["number"]
            print(f"  skip    #{numbers[item['id']]:<4} {item['title']}")
            continue
        print(f"  create  {item['title']}  {meta}")
        if dry:
            continue
        cmd = ["issue", "create", "--title", item["title"], "--body-file", "-",
               "--label", ",".join(item["labels"])]
        if item.get("milestone"):
            cmd += ["--milestone", item["milestone"]]
        url = gh(*cmd, input_text=build_body(item, by_id)).strip().splitlines()[-1]
        numbers[item["id"]] = int(url.rstrip("/").split("/")[-1])
        existing[item["title"]] = {"number": numbers[item["id"]], "state": "OPEN", "url": url}

    # 4. Sub-issue links (parent -> child)
    print("\n== Sub-issues")
    for item in items:
        parent = item.get("parent")
        if not parent:
            continue
        if dry and (item["id"] not in numbers or parent not in numbers):
            print(f"  link    {by_id[parent]['title'][:12]} -> {item['title']}")
            continue
        p_num, c_num = numbers[parent], numbers[item["id"]]
        children = gh_json("api", f"repos/{repo}/issues/{p_num}/sub_issues?per_page=100") or []
        if any(c["number"] == c_num for c in children):
            print(f"  skip    #{p_num} -> #{c_num}")
            continue
        print(f"  link    #{p_num} -> #{c_num}")
        if dry:
            continue
        child_id = gh_json("api", f"repos/{repo}/issues/{c_num}")["id"]
        try:
            gh("api", f"repos/{repo}/issues/{p_num}/sub_issues", "-X", "POST",
               "-F", f"sub_issue_id={child_id}")
        except RuntimeError as err:
            # Fallback: task list entry in the parent body
            print(f"    sub-issue API failed ({err}); adding task-list entry instead")
            body = gh_json("issue", "view", str(p_num), "--json", "body")["body"]
            if f"#{c_num}" not in body:
                gh("issue", "edit", str(p_num), "--body-file", "-",
                   input_text=body + f"\n- [ ] #{c_num}\n")

    # 5. Project items and fields (Status, Priority)
    print("\n== Project")
    projects = gh_json("project", "list", "--owner", owner, "--format", "json")["projects"]
    project = next(p for p in projects if p["title"] == backlog["project_title"])
    p_num = str(project["number"])
    p_id = gh_json("project", "view", p_num, "--owner", owner, "--format", "json")["id"]
    fields = {f["name"]: f for f in gh_json("project", "field-list", p_num, "--owner", owner,
                                            "--format", "json")["fields"]}
    option_ids = {name: {o["name"]: o["id"] for o in fields[name]["options"]} for name in ("Status", "Priority")}
    proj_items = {}
    for it in gh_json("project", "item-list", p_num, "--owner", owner, "--format", "json",
                      "--limit", "500")["items"]:
        if it.get("content", {}).get("number"):
            proj_items[it["content"]["number"]] = it
    print(f"  project #{p_num} '{project['title']}', {len(proj_items)} existing items")

    for item in items:
        num = numbers.get(item["id"])
        wanted = {"Status": item["status"], "Priority": item.get("priority")}
        if num is None:  # dry run, issue not yet created
            print(f"  add     {item['id']:<7} Status={wanted['Status']}"
                  f"{' Priority=' + wanted['Priority'] if wanted['Priority'] else ''}")
            continue
        proj_item = proj_items.get(num)
        if proj_item is None:
            print(f"  add     #{num} {item['id']}")
            if dry:
                continue
            proj_item = gh_json("project", "item-add", p_num, "--owner", owner,
                                "--url", existing[item["title"]]["url"], "--format", "json")
        for field, value in wanted.items():
            if not value:
                continue
            current = proj_item.get(field.lower())
            if current == value:
                continue
            print(f"  set     #{num} {field}={value}")
            if not dry:
                gh("project", "item-edit", "--id", proj_item["id"], "--project-id", p_id,
                   "--field-id", fields[field]["id"],
                   "--single-select-option-id", option_ids[field][value])

    # 6. Close completed issues
    print("\n== Close completed")
    for item in items:
        if not item.get("closed"):
            continue
        state = existing.get(item["title"], {}).get("state", "OPEN")
        if state == "CLOSED":
            print(f"  skip    {item['title']}")
            continue
        print(f"  close   {item['title']}")
        if not dry:
            gh("issue", "close", str(numbers[item["id"]]), "--reason", "completed")

    # 7. Close milestones whose target state is closed
    print("\n== Close milestones")
    for ms in backlog["milestones"]:
        if ms["state"] != "closed":
            continue
        current = existing_ms.get(ms["title"])
        if current and current.get("state") == "closed":
            print(f"  skip    {ms['title']}")
            continue
        print(f"  close   {ms['title']}")
        if not dry:
            gh("api", f"repos/{repo}/milestones/{current['number']}", "-X", "PATCH", "-f", "state=closed")

    print(f"\nDone ({mode}).")


if __name__ == "__main__":
    main()
