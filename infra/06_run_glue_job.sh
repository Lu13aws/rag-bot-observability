#!/usr/bin/env bash
# Step 3.6: run the Glue job, wait for the result and check the output.
# Note: the job overwrites s3://<bucket>/processed/rag_query_log/ on each run.
source "$(dirname "$0")/lib.sh"

RUN_ID="$(run aws glue start-job-run --job-name "$GLUE_JOB" --query JobRunId --output text | tail -n 1)"
[[ "$DRY_RUN" == "1" ]] && exit 0
echo "Started run $RUN_ID"

while true; do
  STATE="$(aws glue get-job-run --job-name "$GLUE_JOB" --run-id "$RUN_ID" --query JobRun.JobRunState --output text)"
  case "$STATE" in
    SUCCEEDED|FAILED|ERROR|TIMEOUT|STOPPED) break ;;
  esac
  echo "  state: $STATE"
  sleep 20
done

aws glue get-job-run --job-name "$GLUE_JOB" --run-id "$RUN_ID" \
  --query 'JobRun.{State:JobRunState,ExecutionSeconds:ExecutionTime,DPUSeconds:DPUSeconds,GlueVersion:GlueVersion,Error:ErrorMessage}' \
  --output table
[[ "$STATE" == "SUCCEEDED" ]] || exit 1

echo "dt partitions in processed/: $(aws s3 ls "s3://$BUCKET/processed/rag_query_log/" | grep -c 'PRE dt=')"
echo "Row count logged by the job:"
aws logs filter-log-events --log-group-name /aws-glue/jobs/output \
  --log-stream-name-prefix "$RUN_ID" --filter-pattern '"ROW_COUNT"' \
  --query 'events[].message' --output text 2>/dev/null || echo "  (not found - checked in step 4 with Athena)"
