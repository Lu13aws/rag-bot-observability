"""Read-only check: compare the GitHub backlog with tools/backlog/backlog.json.

Prints one row per issue (number, state, milestone, parent, project Status and
Priority) and lists every mismatch: state, close reason, status, priority,
parent (sub-issue link), milestone, labels and duplicate project items.
Separate from create_backlog.py on purpose: generation and verification stay
independent. Exit code 1 if any mismatch is found.

Usage:
    python tools/verify_backlog.py
"""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from create_backlog import build_body, normalize  # same body format as the generator

BACKLOG = Path(__file__).resolve().parent / "backlog" / "backlog.json"


def gh(*args: str):
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def main() -> None:
    backlog = json.loads(BACKLOG.read_text(encoding="utf-8"))
    repo = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    owner = repo.split("/")[0]

    projects = gh("project", "list", "--owner", owner, "--format", "json")["projects"]
    project = next(p for p in projects if p["title"] == backlog["project_title"])
    items = gh("project", "item-list", str(project["number"]), "--owner", owner,
               "--format", "json", "--limit", "500")["items"]
    with_number = [it for it in items if it.get("content", {}).get("number")]
    item_count = Counter(it["content"]["number"] for it in with_number)
    fields = {it["content"]["number"]: it for it in with_number}

    issues = {i["title"]: i for i in gh("issue", "list", "--state", "all", "--limit", "500",
                                         "--json", "number,title,state,stateReason,milestone,labels,body")}
    by_id = {b["id"]: b for b in backlog["issues"]}
    missing = [b["title"] for b in backlog["issues"] if b["title"] not in issues]
    if missing:
        print("Missing issues:\n  " + "\n  ".join(missing))
        sys.exit(1)

    parent_of = {}
    for b in backlog["issues"]:
        if b["type"] in ("epic", "feature"):
            num = issues[b["title"]]["number"]
            for child in gh("api", f"repos/{repo}/issues/{num}/sub_issues?per_page=100"):
                parent_of[child["number"]] = num

    mismatches = []
    print("| # | ID | Title | State | Milestone | Parent | Status | Priority |")
    print("|---|---|---|---|---|---|---|---|")
    for b in backlog["issues"]:
        issue = issues[b["title"]]
        num = issue["number"]
        field = fields.get(num, {})
        state = "closed" if issue["state"] == "CLOSED" else "open"
        milestone = (issue["milestone"] or {}).get("title")
        parent = parent_of.get(num)
        expected_parent = issues[by_id[b["parent"]]["title"]]["number"] if b.get("parent") else None
        print(f"| {num} | {b['id']} | {b['title'].split('] ', 1)[1]} | {state} | {milestone or '-'} | "
              f"{'#' + str(parent) if parent else '-'} | {field.get('status', '-')} | "
              f"{field.get('priority') or '-'} |")

        checks = [
            (state == ("closed" if b.get("closed") else "open"), "state"),
            (state == "open" or issue.get("stateReason") == "COMPLETED", "close reason"),
            (field.get("status") == b["status"], "status"),
            ((field.get("priority") or None) == b.get("priority"), "priority"),
            (parent == expected_parent, "parent"),
            (milestone == b.get("milestone"), "milestone"),
            (item_count[num] == 1, f"project items = {item_count[num]}"),
            (sorted(l["name"] for l in issue["labels"]) == sorted(b["labels"]), "labels"),
            (normalize(issue.get("body") or "") == normalize(build_body(b, by_id)), "body"),
        ]
        mismatches += [f"#{num} {b['id']}: {what}" for ok, what in checks if not ok]

    milestones = gh("api", f"repos/{repo}/milestones?state=all")
    expected_ms = {m["title"]: m["state"] for m in backlog["milestones"]}
    for m in milestones:
        if m["title"] in expected_ms and m["state"] != expected_ms[m["title"]]:
            mismatches.append(f"milestone {m['title']}: state {m['state']}")

    print("\nMilestones: " + ", ".join(
        f"{m['title']} ({m['state']}, due {m['due_on'][:10]}, "
        f"{m['open_issues']} open / {m['closed_issues']} closed)" for m in milestones))
    print(f"Issues: {len(issues)} | project items: {sum(item_count.values())} "
          f"(unique {len(item_count)}) | sub-issue links: {len(parent_of)}")
    print("Mismatches: " + ("none" if not mismatches else "\n  " + "\n  ".join(mismatches)))
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
