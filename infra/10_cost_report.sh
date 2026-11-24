#!/usr/bin/env bash
# Read-only cost report for the current month (Cost Explorer).
# Each Cost Explorer API request costs 0.01 USD; this script makes 3 requests.
# Usage: bash infra/10_cost_report.sh [YYYY-MM-DD start] [YYYY-MM-DD end, exclusive]
set -euo pipefail
cd "$(dirname "$0")/.."

START="${1:-$(date +%Y-%m-01)}"
END="${2:-$(date -d tomorrow +%Y-%m-%d)}"
CE=(aws ce get-cost-and-usage --region us-east-1 --time-period "Start=$START,End=$END" --metrics UnblendedCost --output json)
if [[ -x .venv/Scripts/python.exe ]]; then PY=.venv/Scripts/python.exe; else PY=.venv/bin/python; fi

echo "== 1/3 Cost by service ($START to $END, end exclusive)"
"${CE[@]}" --granularity MONTHLY --group-by Type=DIMENSION,Key=SERVICE | "$PY" -I -c '
import json, sys
groups = [g for r in json.load(sys.stdin)["ResultsByTime"] for g in r["Groups"]]
rows = sorted(((g["Keys"][0], float(g["Metrics"]["UnblendedCost"]["Amount"])) for g in groups), key=lambda x: -x[1])
for name, usd in rows:
    if usd >= 0.005: print(f"{usd:10.2f} USD  {name}")
print(f"{sum(u for _, u in rows):10.2f} USD  TOTAL")'

echo; echo "== 2/3 Cost by service and usage type (top 25)"
"${CE[@]}" --granularity MONTHLY --group-by Type=DIMENSION,Key=SERVICE Type=DIMENSION,Key=USAGE_TYPE | "$PY" -I -c '
import json, sys
groups = [g for r in json.load(sys.stdin)["ResultsByTime"] for g in r["Groups"]]
rows = sorted(((g["Keys"][0], g["Keys"][1], float(g["Metrics"]["UnblendedCost"]["Amount"])) for g in groups), key=lambda x: -x[2])
for svc, usage, usd in rows[:25]:
    if usd >= 0.005: print(f"{usd:10.2f} USD  {svc:<45} {usage}")'

echo; echo "== 3/3 Daily cost (total and top service per day)"
"${CE[@]}" --granularity DAILY --group-by Type=DIMENSION,Key=SERVICE | "$PY" -I -c '
import json, sys
for r in json.load(sys.stdin)["ResultsByTime"]:
    rows = sorted(((g["Keys"][0], float(g["Metrics"]["UnblendedCost"]["Amount"])) for g in r["Groups"]), key=lambda x: -x[1])
    total = sum(u for _, u in rows)
    top = f"{rows[0][0]} {rows[0][1]:.2f}" if rows else "-"
    day = r["TimePeriod"]["Start"]
    print(f"{day}  {total:7.2f} USD   top: {top}")'
