"""Compare the Athena KPI views with the local validator (S2.3.2, NFR-04).

1. Reads all rows of the Athena view v_kpi_all (one row per KPI, grain, period).
2. Calculates the same KPIs locally with ingestion/validate_sample_logs.py.
3. Compares value and flags (is_complete_period, is_evaluated, target_breached).

Tolerances (docs/01-requirements.md, section 3.1):
- KPI-01 latency: +-50 ms
- KPI-02 error rate: +-1 % relative OR +-0.2 percentage points absolute
- KPI-03 to KPI-06: +-1 % relative
- KPI-07 query volume: exact match
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
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ingestion"))
import validate_sample_logs as v  # noqa: E402

KPIS = ["KPI-01", "KPI-02", "KPI-03", "KPI-04", "KPI-05", "KPI-06", "KPI-07"]
TARGET_GRAIN = {"KPI-01": "day", "KPI-02": "day", "KPI-03": "week", "KPI-04": "week",
                "KPI-05": "week", "KPI-06": "month"}
QUERY = ("SELECT kpi_id, grain, period_label, kpi_value, sample_size, "
         "is_complete_period, is_evaluated, target_breached FROM v_kpi_all")


# --- tolerance rules (section 3.1) ------------------------------------------

EPS = 1e-12  # limits are inclusive; ignore floating-point noise at the boundary


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


def athena_rows(cfg: dict) -> list[dict]:
    region = ["--region", cfg["AWS_REGION"]]
    qid = aws("athena", "start-query-execution", "--work-group", cfg["PROJECT"],
              "--query-execution-context", f"Database={cfg['GLUE_DATABASE']}",
              "--query-string", QUERY, *region)["QueryExecutionId"]
    while True:
        status = aws("athena", "get-query-execution", "--query-execution-id", qid, *region)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)
    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena query {state}: {status['QueryExecution']['Status'].get('StateChangeReason')}")
    stats = status["QueryExecution"]["Statistics"]
    print(f"Athena: {stats['DataScannedInBytes']:,} bytes scanned, "
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

def expected_rows() -> dict:
    rows, _ = v.load_rows(ROOT / "sample-data" / "raw")
    pricing = v.load_pricing(ROOT / "sample-data" / "model_pricing.csv")
    data_start = date.fromisoformat(min(r["dt"] for r in rows))
    data_end = date.fromisoformat(max(r["dt"] for r in rows))

    groups, bounds = defaultdict(list), {}
    for r in rows:
        for grain in ("day", "week", "month"):
            key, first, last = v.period_of(r["dt"], grain)
            groups[(grain, key)].append(r)
            bounds[(grain, key)] = (first, last)

    expected = {}
    for (grain, key), group in groups.items():
        values = v.kpis(group, pricing)
        first, last = bounds[(grain, key)]
        complete = first >= data_start and last <= data_end
        for kpi in KPIS:
            value = values[kpi]
            if value is None:
                continue
            evaluated = False
            breached = False
            if kpi in TARGET_GRAIN:
                min_ok = not ((kpi == "KPI-02" and values["KPI-07"] < 200)
                              or (kpi == "KPI-04" and values["_rated"] < 30))
                evaluated = grain == TARGET_GRAIN[kpi] and complete and min_ok
                breached = evaluated and v.TARGETS[kpi][2](value)
            expected[(kpi, grain, key)] = {
                "value": float(value), "complete": complete,
                "evaluated": evaluated, "breached": breached,
            }
    return expected


# --- comparison -----------------------------------------------------------------

def to_bool(text: str | None) -> bool:
    return str(text).lower() == "true"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=2, help="sample rows per KPI to print")
    args = parser.parse_args()

    expected = expected_rows()
    actual = {}
    for row in athena_rows(load_config()):
        if row["kpi_value"] is None:
            continue  # same as the validator: no value for empty populations
        actual[(row["kpi_id"], row["grain"], row["period_label"])] = {
            "value": float(row["kpi_value"]),
            "complete": to_bool(row["is_complete_period"]),
            "evaluated": to_bool(row["is_evaluated"]),
            "breached": to_bool(row["target_breached"]),
        }

    mismatches = []
    for key in sorted(set(expected) - set(actual)):
        mismatches.append(f"{key}: missing in Athena")
    for key in sorted(set(actual) - set(expected)):
        mismatches.append(f"{key}: missing in validator")

    max_diff = defaultdict(float)
    compared = 0
    for key in sorted(set(expected) & set(actual)):
        kpi = key[0]
        e, a = expected[key], actual[key]
        compared += 1
        max_diff[kpi] = max(max_diff[kpi], abs(a["value"] - e["value"]))
        if not within_tolerance(kpi, a["value"], e["value"]):
            mismatches.append(f"{key}: value athena={a['value']} validator={e['value']}")
        for flag in ("complete", "evaluated", "breached"):
            if a[flag] != e[flag]:
                mismatches.append(f"{key}: {flag} athena={a[flag]} validator={e[flag]}")

    print(f"Rows: validator={len(expected)}, athena={len(actual)}, compared={compared}")
    print("Max absolute difference per KPI: "
          + ", ".join(f"{k}={max_diff[k]:.3g}" for k in KPIS))
    print(f"Evaluated periods: {sum(e['evaluated'] for e in expected.values())}, "
          f"breaches: {sum(e['breached'] for e in expected.values())} (validator) / "
          f"{sum(a['breached'] for a in actual.values())} (athena)")

    print("\nSamples (kpi, grain, period: athena | validator | evaluated | breached):")
    for kpi in KPIS:
        keys = [k for k in sorted(set(expected) & set(actual)) if k[0] == kpi]
        picks = [k for k in keys if expected[k]["breached"]][:1]
        picks += [k for k in keys if k not in picks and k[1] == TARGET_GRAIN.get(kpi, "day")][:args.samples - len(picks)]
        for k in picks:
            print(f"  {k[0]} {k[1]:<5} {k[2]:<10}  {actual[k]['value']:.6g} | {expected[k]['value']:.6g}"
                  f" | {actual[k]['evaluated']} | {actual[k]['breached']}")

    print("\nMismatches: " + ("none" if not mismatches else f"{len(mismatches)}\n  " + "\n  ".join(mismatches[:30])))
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
