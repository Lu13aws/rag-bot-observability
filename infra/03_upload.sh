#!/usr/bin/env bash
# Step 3.2: validate the local sample data, then upload data and Glue script.
# Uploads only add or replace files; nothing in S3 is deleted.
source "$(dirname "$0")/lib.sh"

if [[ -x .venv/Scripts/python.exe ]]; then PY=.venv/Scripts/python.exe; else PY=.venv/bin/python; fi

# Abort before any upload if the data does not pass validation
"$PY" ingestion/validate_sample_logs.py > /dev/null
echo "Local validation passed."

run aws s3 sync sample-data/raw "s3://$BUCKET/raw/rag_query_log/" \
  --exclude "*" --include "dt=*/queries.jsonl" --only-show-errors

run aws s3 cp sample-data/model_pricing.csv \
  "s3://$BUCKET/reference/model_pricing/model_pricing.csv" --only-show-errors

run aws s3 cp glue/rag_query_log_json_to_parquet.py \
  "s3://$BUCKET/scripts/rag_query_log_json_to_parquet.py" --only-show-errors

if [[ "$DRY_RUN" != "1" ]]; then
  echo "dt partitions in raw/: $(aws s3 ls "s3://$BUCKET/raw/rag_query_log/" | grep -c 'PRE dt=')"
fi
