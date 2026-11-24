"""Generate synthetic query logs for a fictional RAG assistant.

Output: one JSON Lines file per local day (Europe/Zurich) in Hive layout,
    <out>/dt=YYYY-MM-DD/queries.jsonl
One line = one query, fields as defined in docs/01-requirements.md, section 5.1.

The output is fully reproducible: the same --seed, --start and --days always
produce the same files (including query_id).

Usage:
    python ingestion/generate_sample_logs.py
    python ingestion/generate_sample_logs.py --seed 42 --start 2026-08-01 --days 90
"""

import argparse
import json
import math
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Zurich")
TIMEOUT_MS = 30_000  # assumption A-2

# --- Base distributions (docs/01-requirements.md, section 5.3) ---------------
WEEKDAY_VOLUME = 400
WEEKEND_VOLUME = 80
USER_GROUPS = [("team_a", 0.6), ("team_b", 0.4)]
MODELS = [("model-small", 0.7), ("model-large", 0.3)]
MEDIAN_LATENCY_MS = {"model-small": 3_000, "model-large": 4_500}
LATENCY_SIGMA = 0.3  # spread of the lognormal distribution
BASE_ERROR_RATE = 0.005
BASE_TIMEOUT_RATE = 0.003
BASE_NO_SOURCE_RATE = 0.06
FEEDBACK_RATE = 0.08  # share of successful queries that get rated
POSITIVE_WITH_SOURCES = 0.85
POSITIVE_WITHOUT_SOURCES = 0.40

# --- Scenarios (day numbers start at 1 = --start) ----------------------------
FAULTY_RELEASE_DAYS = range(46, 49)  # app_version 1.1.0, more errors
FAULTY_RELEASE_ERROR_RATE = 0.05
LATENCY_SPIKE_DAYS = range(60, 63)
LATENCY_SPIKE_FACTOR = 2.0
KNOWLEDGE_GAP_DAYS = range(73, 80)  # one full ISO week (Mon-Sun)
KNOWLEDGE_GAP_NO_SOURCE_RATE = 0.25


def hour_weight(hour: int) -> float:
    """Relative query volume per local hour: peak during office hours."""
    if 8 <= hour < 18:
        return 1.0
    if hour in (7, 18, 19):
        return 0.4
    return 0.05


HOUR_WEIGHTS = [hour_weight(h) for h in range(24)]


def pick(rng: random.Random, options: list[tuple[str, float]]) -> str:
    values, weights = zip(*options)
    return rng.choices(values, weights=weights)[0]


def app_version(day_no: int) -> str:
    if day_no < FAULTY_RELEASE_DAYS.start:
        return "1.0.0"
    if day_no in FAULTY_RELEASE_DAYS:
        return "1.1.0"
    return "1.1.1"


def daily_volume(rng: random.Random, local_day: date) -> int:
    mean = WEEKEND_VOLUME if local_day.weekday() >= 5 else WEEKDAY_VOLUME
    # Normal approximation of a Poisson distribution
    return max(0, round(rng.gauss(mean, math.sqrt(mean))))


def local_timestamp(rng: random.Random, local_day: date) -> datetime:
    hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
    second_of_hour = rng.uniform(0, 3600)
    naive = datetime(local_day.year, local_day.month, local_day.day, hour) + timedelta(
        seconds=second_of_hour
    )
    return naive.replace(tzinfo=LOCAL_TZ)


def make_query(rng: random.Random, day_no: int, local_day: date) -> dict:
    event_local = local_timestamp(rng, local_day)
    event_utc = event_local.astimezone(timezone.utc)
    model_id = pick(rng, MODELS)

    error_rate = FAULTY_RELEASE_ERROR_RATE if day_no in FAULTY_RELEASE_DAYS else BASE_ERROR_RATE
    no_source_rate = (
        KNOWLEDGE_GAP_NO_SOURCE_RATE if day_no in KNOWLEDGE_GAP_DAYS else BASE_NO_SOURCE_RATE
    )

    roll = rng.random()
    if roll < error_rate:
        status = "error"
    elif roll < error_rate + BASE_TIMEOUT_RATE:
        status = "timeout"
    else:
        status = "success"

    sources_count = 0 if rng.random() < no_source_rate else rng.randint(1, 5)
    tokens_in = rng.randint(500, 800) + sources_count * rng.randint(300, 350)
    tokens_out = 0
    error_type = None
    feedback = None

    if status == "success":
        median = MEDIAN_LATENCY_MS[model_id]
        if day_no in LATENCY_SPIKE_DAYS:
            median *= LATENCY_SPIKE_FACTOR
        latency_ms = round(rng.lognormvariate(math.log(median), LATENCY_SIGMA))
        if latency_ms >= TIMEOUT_MS:
            # Rule A-2: anything at or above the limit is a timeout
            status = "timeout"
        else:
            tokens_out = rng.randint(150, 500)
            if rng.random() < FEEDBACK_RATE:
                p_positive = POSITIVE_WITH_SOURCES if sources_count > 0 else POSITIVE_WITHOUT_SOURCES
                feedback = 1 if rng.random() < p_positive else -1

    if status == "timeout":
        latency_ms = TIMEOUT_MS
        error_type = "llm_timeout"
    elif status == "error":
        latency_ms = rng.randint(200, 2_000)
        if day_no in FAULTY_RELEASE_DAYS or rng.random() < 0.5:
            error_type = "llm_api"
        else:
            error_type = "retrieval"
            sources_count = 0
            tokens_in = 0

    return {
        "query_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
        "event_ts": event_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "dt": local_day.isoformat(),
        "status": status,
        "error_type": error_type,
        "latency_ms": latency_ms,
        "sources_count": sources_count,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "feedback": feedback,
        "model_id": model_id,
        "app_version": app_version(day_no),
        "user_group": pick(rng, USER_GROUPS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 8, 1))
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--out", type=Path, default=Path("sample-data/raw"))
    args = parser.parse_args()

    rng = random.Random(args.seed)
    total = 0
    for day_no in range(1, args.days + 1):
        local_day = args.start + timedelta(days=day_no - 1)
        rows = [make_query(rng, day_no, local_day) for _ in range(daily_volume(rng, local_day))]
        rows.sort(key=lambda r: r["event_ts"])

        day_dir = args.out / f"dt={local_day.isoformat()}"
        day_dir.mkdir(parents=True, exist_ok=True)
        with open(day_dir / "queries.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        total += len(rows)

    end = args.start + timedelta(days=args.days - 1)
    print(f"Wrote {total} queries for {args.start} to {end} into {args.out}")


if __name__ == "__main__":
    main()
