"""Validate synthetic query logs and print KPI results.

Part 1 checks the data against the data model (docs/01-requirements.md,
section 5.1). Part 2 calculates the KPIs from docs/02-kpi-catalog.md per
target grain and lists every period that breaches its target.

This script does not import the generator on purpose: validation must be
independent of generation.

Exit code 0 = all checks passed, 1 = at least one check failed.

Usage:
    python ingestion/validate_sample_logs.py
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Zurich")
TIMEOUT_MS = 30_000

FIELDS = {
    "query_id": str,
    "event_ts": str,
    "dt": str,
    "status": str,
    "error_type": (str, type(None)),
    "latency_ms": int,
    "sources_count": int,
    "tokens_in": int,
    "tokens_out": int,
    "feedback": (int, type(None)),
    "model_id": str,
    "app_version": str,
    "user_group": str,
}
STATUSES = {"success", "error", "timeout"}
MODELS = {"model-small", "model-large"}
USER_GROUPS = {"team_a", "team_b"}
FEEDBACK_VALUES = {1, -1, None}


# --- Part 1: data checks -----------------------------------------------------

def load_rows(raw_dir: Path) -> tuple[list[dict], list[str]]:
    rows, errors = [], []
    for path in sorted(raw_dir.glob("dt=*/queries.jsonl")):
        folder_dt = path.parent.name.removeprefix("dt=")
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                row = json.loads(line)
                if row.get("dt") != folder_dt:
                    errors.append(f"{path}:{line_no} dt {row.get('dt')} != folder {folder_dt}")
                rows.append(row)
    return rows, errors


def check_row(row: dict) -> list[str]:
    qid = row.get("query_id", "?")
    problems = []
    if set(row) != set(FIELDS):
        return [f"{qid}: fields {sorted(set(row) ^ set(FIELDS))} missing or unexpected"]
    for field, expected in FIELDS.items():
        # bool is a subclass of int in Python, so reject it explicitly
        if isinstance(row[field], bool) or not isinstance(row[field], expected):
            problems.append(f"{qid}: {field} has type {type(row[field]).__name__}")
    if problems:
        return problems

    if row["status"] not in STATUSES:
        problems.append(f"{qid}: status {row['status']!r} not allowed")
    if row["model_id"] not in MODELS:
        problems.append(f"{qid}: model_id {row['model_id']!r} not allowed")
    if row["user_group"] not in USER_GROUPS:
        problems.append(f"{qid}: user_group {row['user_group']!r} not allowed")
    if row["feedback"] not in FEEDBACK_VALUES:
        problems.append(f"{qid}: feedback {row['feedback']!r} not allowed")

    local_date = (
        datetime.fromisoformat(row["event_ts"].replace("Z", "+00:00")).astimezone(LOCAL_TZ).date()
    )
    if row["dt"] != local_date.isoformat():
        problems.append(f"{qid}: dt {row['dt']} != local date of event_ts {local_date}")

    is_timeout = row["status"] == "timeout"
    if is_timeout != (row["latency_ms"] >= TIMEOUT_MS):
        problems.append(f"{qid}: status {row['status']} with latency_ms {row['latency_ms']} (rule A-2)")
    if (row["status"] == "success") != (row["error_type"] is None):
        problems.append(f"{qid}: error_type {row['error_type']!r} with status {row['status']}")
    for field in ("latency_ms", "sources_count", "tokens_in", "tokens_out"):
        if row[field] < 0:
            problems.append(f"{qid}: {field} is negative")
    return problems


def run_checks(rows: list[dict], load_errors: list[str]) -> bool:
    errors = list(load_errors)
    seen = set()
    for row in rows:
        errors.extend(check_row(row))
        if row.get("query_id") in seen:
            errors.append(f"{row.get('query_id')}: duplicate query_id")
        seen.add(row.get("query_id"))

    print(f"Data checks on {len(rows)} rows: ", end="")
    if not rows:
        print("FAILED - no rows found")
        return False
    if errors:
        print(f"FAILED - {len(errors)} problem(s), first 10:")
        for e in errors[:10]:
            print(f"  - {e}")
        return False
    print("all passed")
    return True


# --- Part 2: KPIs (formulas from docs/02-kpi-catalog.md) ---------------------

def load_pricing(path: Path) -> dict[str, list[tuple[date, float, float]]]:
    pricing = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pricing[r["model_id"]].append(
                (date.fromisoformat(r["valid_from"]), float(r["price_in_per_1k"]), float(r["price_out_per_1k"]))
            )
    for prices in pricing.values():
        prices.sort()
    return pricing


def query_cost(row: dict, pricing: dict) -> float:
    query_date = date.fromisoformat(row["dt"])
    valid = [p for p in pricing[row["model_id"]] if p[0] <= query_date]
    _, price_in, price_out = valid[-1]  # latest valid_from on or before the query date
    return row["tokens_in"] / 1000 * price_in + row["tokens_out"] / 1000 * price_out


def p95_nearest_rank(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def kpis(rows: list[dict], pricing: dict) -> dict:
    success = [r for r in rows if r["status"] == "success"]
    rated = [r for r in rows if r["feedback"] is not None]
    return {
        "KPI-01": p95_nearest_rank([r["latency_ms"] for r in success]),
        "KPI-02": ratio(sum(r["status"] != "success" for r in rows), len(rows)),
        "KPI-03": ratio(sum(r["sources_count"] == 0 for r in success), len(success)),
        "KPI-04": ratio(sum(r["feedback"] == 1 for r in rated), len(rated)),
        "KPI-05": ratio(len(rated), len(rows)),
        "KPI-06": ratio(sum(query_cost(r, pricing) for r in rows), len(rows)) if rows else None,
        "KPI-07": len(rows),
        "_rated": len(rated),
    }


# KPI ID -> (name, target grain, breach test, display format)
TARGETS = {
    "KPI-01": ("p95 latency < 8,000 ms", "day", lambda v: v >= 8_000, "{:,.0f} ms"),
    "KPI-02": ("Error rate < 2 %", "day", lambda v: v >= 0.02, "{:.2%}"),
    "KPI-03": ("No-source share < 10 %", "week", lambda v: v >= 0.10, "{:.2%}"),
    "KPI-04": ("Positive feedback >= 75 %", "week", lambda v: v < 0.75, "{:.2%}"),
    "KPI-05": ("Feedback rate >= 5 %", "week", lambda v: v < 0.05, "{:.2%}"),
    "KPI-06": ("Cost per query <= 0.02 USD", "month", lambda v: v > 0.02, "{:.4f} USD"),
}


def period_of(dt: str, grain: str) -> tuple[str, date, date]:
    """Return (label, first day, last day) of the period that contains dt."""
    d = date.fromisoformat(dt)
    if grain == "day":
        return dt, d, d
    if grain == "week":
        iso = d.isocalendar()
        first = d - timedelta(days=d.weekday())
        return f"{iso.year}-W{iso.week:02d}", first, first + timedelta(days=6)
    first = d.replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    return f"{d.year}-{d.month:02d}", first, next_month - timedelta(days=1)


def report_kpis(rows: list[dict], pricing: dict) -> None:
    overall = kpis(rows, pricing)
    print("\nKPIs over the full period:")
    for kpi_id, (name, *_rest, fmt) in TARGETS.items():
        print(f"  {kpi_id} {name:<28} {fmt.format(overall[kpi_id])}")
    print(f"  KPI-07 Query volume                 {overall['KPI-07']:,}")

    data_start = date.fromisoformat(min(r["dt"] for r in rows))
    data_end = date.fromisoformat(max(r["dt"] for r in rows))

    print(f"\nTarget breaches per target grain (data period {data_start} to {data_end}):")
    for kpi_id, (name, grain, breached, fmt) in TARGETS.items():
        groups = defaultdict(list)
        bounds = {}
        for r in rows:
            key, first, last = period_of(r["dt"], grain)
            groups[key].append(r)
            bounds[key] = (first, last)
        hits, incomplete = [], []
        for key in sorted(groups):
            first, last = bounds[key]
            if first < data_start or last > data_end:
                incomplete.append(key)  # incomplete edge period: not evaluated
                continue
            values = kpis(groups[key], pricing)
            value = values[kpi_id]
            if value is None:
                continue
            if kpi_id == "KPI-02" and values["KPI-07"] < 200:
                continue  # not evaluated below 200 queries
            if kpi_id == "KPI-04" and values["_rated"] < 30:
                continue  # not evaluated below 30 rated queries
            if breached(value):
                hits.append(f"{key} ({fmt.format(value)}, n={values['KPI-07']})")
        skipped = f", not evaluated (incomplete): {', '.join(incomplete)}" if incomplete else ""
        evaluated = len(groups) - len(incomplete)
        print(f"  {kpi_id} {name} [{grain}]: {len(hits)} of {evaluated} periods{skipped}")
        for h in hits:
            print(f"      {h}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=Path("sample-data/raw"))
    parser.add_argument("--pricing", type=Path, default=Path("sample-data/model_pricing.csv"))
    args = parser.parse_args()

    rows, load_errors = load_rows(args.raw)
    passed = run_checks(rows, load_errors)
    if rows and passed:
        report_kpis(rows, load_pricing(args.pricing))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
