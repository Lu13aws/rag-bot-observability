"""Compare the Athena KPI views with the local validator (S2.3.2, S3.2.0, NFR-04).

1. Reads v_kpi_all (one row per KPI, grain, period and dimension combination
   of user_group, model_id and app_version, each incl. 'all').
2. Calculates the same KPIs locally with ingestion/validate_sample_logs.py,
   using the same dimension combinations as sql/views/00_v_query_period.sql.
3. Compares value and flags (is_complete_period, is_evaluated, target_breached).
4. Reads v_failures_by_type (FR-06) and checks the counts against the
   validator and against the KPI-02 numerator in Athena.

Tolerances (docs/01-requirements.md, section 3.1):
- KPI-01 latency: +-50 ms
- KPI-02 error rate: +-1 % relative OR +-0.2 percentage points absolute
- KPI-03 to KPI-06: +-1 % relative
- KPI-07 query volume and all failure counts: exact match
Flags must match exactly. Nothing is corrected automatically.

Exit code 0 = no mismatch, 1 = at least one mismatch.

Usage:
    python ingestion/compare_kpis.py [--samples N]
"""

import argparse
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ingestion"))
import validate_sample_logs as v  # noqa: E402

KPIS = ["KPI-01", "KPI-02", "KPI-03", "KPI-04", "KPI-05", "KPI-06", "KPI-07"]
TARGET_GRAIN = {"KPI-01": "day", "KPI-02": "day", "KPI-03": "week", "KPI-04": "week",
                "KPI-05": "week", "KPI-06": "month"}
DIMS = ("user_group", "model_id", "app_version")
ALL = ("all", "all", "all")
KPI_QUERY = ("SELECT kpi_id, grain, period_label, user_group, model_id, app_version, "
             "numerator, kpi_value, is_complete_period, is_evaluated, target_breached "
             "FROM v_kpi_all")
FAILURE_QUERY = ("SELECT grain, period_label, user_group, model_id, app_version, "
                 "status, error_type, failed_queries FROM v_failures_by_type")
EPS = 1e-12  # limits are inclusive; ignore floating-point noise at the boundary


# --- tolerance rules (section 3.1) ------------------------------------------

def within_tolerance(kpi: str, actual: float, expected: float) -> bool:
    diff = abs(actual - expected)
    if kpi == "KPI-01":
        return diff <= 50 + EPS
    if kpi == "KPI-07":
        return actual == expected
    relative_ok = diff <= 0.01 * abs(expected) + EPS
    if kpi == "KPI-02":
        return relative_ok or diff <= 0.002 + EPS  # one of the two limits is enough
    return relative_ok


# --- Athena -------------------------------------------------------------------

def load_config() -> dict:
    cfg = {}
    text = (ROOT / "infra" / "config.env").read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            cfg[key] = value.strip()
    return cfg


def aws(*args: str) -> dict:
    result = subprocess.run(["aws", *args, "--output", "json"], capture_output=True,
                            text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def athena_rows(cfg: dict, query: str) -> list[dict]:
    region = ["--region", cfg["AWS_REGION"]]
    qid = aws("athena", "start-query-execution", "--work-group", cfg["PROJECT"],
              "--query-execution-context", f"Database={cfg['GLUE_DATABASE']}",
              "--query-string", query, *region)["QueryExecutionId"]
    while True:
        status = aws("athena", "get-query-execution", "--query-execution-id", qid, *region)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)
    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena query {state}: {status['QueryExecution']['Status'].get('StateChangeReason')}")
    stats = status["QueryExecution"]["Statistics"]
    print(f"Athena ({query.split('FROM ')[-1]}): {stats['DataScannedInBytes']:,} bytes scanned, "
          f"{stats['TotalExecutionTimeInMillis']:,} ms")

    rows, token, header = [], None, None
    while True:
        page_args = ["athena", "get-query-results", "--query-execution-id", qid,
                     "--max-results", "1000", "--no-paginate", *region]
        if token:
            page_args += ["--next-token", token]
        page = aws(*page_args)
        for r in page["ResultSet"]["Rows"]:
            values = [c.get("VarCharValue") for c in r["Data"]]
            if header is None:
                header = values
                continue
            rows.append(dict(zip(header, values)))
        token = page.get("NextToken")
        if not token:
            return rows


# --- validator ------------------------------------------------------------------

def combinations(row: dict) -> list[tuple]:
    """Same as the UNNEST in v_query_period: own value and 'all' per dimension."""
    return list(product(*[(row[d], "all") for d in DIMS]))


def expected_values() -> tuple[dict, Counter]:
    rows, _ = v.load_rows(ROOT / "sample-data" / "raw")
    pricing = v.load_pricing(ROOT / "sample-data" / "model_pricing.csv")
    data_start = date.fromisoformat(min(r["dt"] for r in rows))
    data_end = date.fromisoformat(max(r["dt"] for r in rows))

    groups, bounds = defaultdict(list), {}
    failures = Counter()
    for r in rows:
        combos = combinations(r)
        for grain in ("day", "week", "month"):
            key, first, last = v.period_of(r["dt"], grain)
            bounds[(grain, key)] = (first, last)
            for combo in combos:
                groups[(grain, key) + combo].append(r)
                if r["status"] != "success":
                    failures[(grain, key) + combo + (r["status"], r["error_type"] or "-")] += 1

    expected = {}
    for (grain, key, *combo), group in groups.items():
        values = v.kpis(group, pricing)
        first, last = bounds[(grain, key)]
        complete = first >= data_start and last <= data_end
        for kpi in KPIS:
            value = values[kpi]
            if value is None:
                continue
            evaluated = breached = False
            if kpi in TARGET_GRAIN:
                # Minimum sample sizes from the KPI catalog, per selection
                min_ok = not ((kpi == "KPI-01" and values["_successful"] < 100)
                              or (kpi == "KPI-02" and values["KPI-07"] < 200)
                              or (kpi == "KPI-04" and values["_rated"] < 30))
                evaluated = grain == TARGET_GRAIN[kpi] and complete and min_ok
                breached = evaluated and v.TARGETS[kpi][2](value)
            expected[(kpi, grain, key, *combo)] = {
                "value": float(value), "complete": complete,
                "evaluated": evaluated, "breached": breached,
            }
    return expected, failures


# --- comparison -----------------------------------------------------------------

def to_bool(text: str | None) -> bool:
    return str(text).lower() == "true"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=2, help="sample rows per KPI to print")
    args = parser.parse_args()
    cfg = load_config()

    expected, expected_failures = expected_values()
    actual, kpi02_numerator = {}, {}
    for row in athena_rows(cfg, KPI_QUERY):
        key = (row["kpi_id"], row["grain"], row["period_label"], *[row[d] for d in DIMS])
        if row["kpi_id"] == "KPI-02":
            kpi02_numerator[key[1:]] = float(row["numerator"])
        if row["kpi_value"] is None:
            continue  # same as the validator: no value for empty populations
        actual[key] = {
            "value": float(row["kpi_value"]),
            "complete": to_bool(row["is_complete_period"]),
            "evaluated": to_bool(row["is_evaluated"]),
            "breached": to_bool(row["target_breached"]),
        }
    actual_failures = Counter()
    for row in athena_rows(cfg, FAILURE_QUERY):
        actual_failures[(row["grain"], row["period_label"], *[row[d] for d in DIMS],
                         row["status"], row["error_type"])] = int(row["failed_queries"])

    mismatches = []
    for key in sorted(set(expected) - set(actual)):
        mismatches.append(f"{key}: missing in Athena")
    for key in sorted(set(actual) - set(expected)):
        mismatches.append(f"{key}: missing in validator")

    max_diff = defaultdict(float)
    common = sorted(set(expected) & set(actual))
    for key in common:
        kpi = key[0]
        e, a = expected[key], actual[key]
        max_diff[kpi] = max(max_diff[kpi], abs(a["value"] - e["value"]))
        if not within_tolerance(kpi, a["value"], e["value"]):
            mismatches.append(f"{key}: value athena={a['value']} validator={e['value']}")
        for flag in ("complete", "evaluated", "breached"):
            if a[flag] != e[flag]:
                mismatches.append(f"{key}: {flag} athena={a[flag]} validator={e[flag]}")

    # FR-06: failure counts vs validator, and sum per period vs KPI-02 numerator
    for key in sorted(set(expected_failures) | set(actual_failures)):
        if expected_failures[key] != actual_failures[key]:
            mismatches.append(f"failures {key}: athena={actual_failures[key]} "
                              f"validator={expected_failures[key]}")
    failure_sums = Counter()
    for key, count in actual_failures.items():
        failure_sums[key[:5]] += count
    for key, numerator in kpi02_numerator.items():
        if failure_sums[key] != numerator:
            mismatches.append(f"failures sum {key}: {failure_sums[key]} != KPI-02 numerator {numerator}")

    all_rows = [k for k in common if tuple(k[3:]) == ALL]
    combos = {tuple(k[3:]) for k in common}
    print(f"\nKPI rows: validator={len(expected)}, athena={len(actual)}, compared={len(common)} "
          f"({len(combos)} dimension combinations; rows with all/all/all: {len(all_rows)})")
    print(f"Failure rows: validator={len(expected_failures)}, athena={len(actual_failures)}; "
          f"checked against {len(kpi02_numerator)} KPI-02 numerators")
    print("Max absolute difference per KPI: "
          + ", ".join(f"{k}={max_diff[k]:.3g}" for k in KPIS))
    print(f"Evaluated: {sum(e['evaluated'] for e in expected.values())}, "
          f"breaches: {sum(e['breached'] for e in expected.values())} (validator) / "
          f"{sum(a['breached'] for a in actual.values())} (athena); "
          f"overall (all/all/all) breaches: {sum(expected[k]['breached'] for k in all_rows)}")

    print("\nSamples (kpi grain period user_group/model_id/app_version: athena | validator | evaluated | breached):")
    for kpi in KPIS:
        keys = [k for k in common if k[0] == kpi and k[1] == TARGET_GRAIN.get(kpi, "day")]
        picks = [k for k in keys if expected[k]["breached"] and tuple(k[3:]) != ALL][:1]
        picks += [k for k in keys if tuple(k[3:]) == ALL][:max(args.samples - len(picks), 1)]
        for k in picks:
            print(f"  {k[0]} {k[1]:<5} {k[2]:<10} {'/'.join(k[3:]):<28} "
                  f"{actual[k]['value']:.6g} | {expected[k]['value']:.6g} | "
                  f"{actual[k]['evaluated']} | {actual[k]['breached']}")

    print("\nMismatches: " + ("none" if not mismatches else f"{len(mismatches)}\n  " + "\n  ".join(mismatches[:30])))
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
