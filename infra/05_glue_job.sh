#!/usr/bin/env bash
# Step 3.4/3.5: Glue Data Catalog database and the ETL job definition.
# Job: 2 x G.1X workers (not the default 10), 10-minute timeout, no retries.
# The table itself is defined with Athena DDL in step 4 (no crawler).
source "$(dirname "$0")/lib.sh"
: "${GLUE_DATABASE:?}" "${GLUE_VERSION:?}"

if aws glue get-database --name "$GLUE_DATABASE" >/dev/null 2>&1; then
  echo "Database $GLUE_DATABASE already exists - skipped."
else
  run aws glue create-database \
    --database-input "Name=$GLUE_DATABASE,Description=RAG assistant monitoring (synthetic data)"
fi

ROLE_ARN="$(aws iam get-role --role-name "$GLUE_ROLE" --query Role.Arn --output text)"
export ROLE_ARN
render infra/glue/job.template.json "$RENDER_DIR/glue-job.json"

if aws glue get-job --job-name "$GLUE_JOB" >/dev/null 2>&1; then
  run aws glue update-job --job-name "$GLUE_JOB" --job-update "file://$RENDER_DIR/glue-job.json"
else
  run aws glue create-job --name "$GLUE_JOB" \
    --cli-input-json "file://$RENDER_DIR/glue-job.json" \
    --tags "Project=$PROJECT"
fi
