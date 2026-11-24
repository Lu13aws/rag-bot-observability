#!/usr/bin/env bash
# Step S2.3.1: Athena workgroup, table definitions and acceptance checks.
# - Workgroup: results in s3://<bucket>/athena-results/ (SSE-S3), settings
#   enforced, scan limit 100 MB per query, tag Project (NFR-03).
# - Tables: sql/01_*.sql and sql/02_*.sql (CREATE ... IF NOT EXISTS).
# - Checks: sql/checks/*.sql, results printed as a table.
source "$(dirname "$0")/lib.sh"
: "${GLUE_DATABASE:?}"
ATHENA_WG="${PROJECT}"

# Run one SQL file in the workgroup, wait for the result, print it.
athena_run() {
  local file="$1" rendered="$RENDER_DIR/$(basename "$1")"
  render "$file" "$rendered"
  echo "== $file"
  local id
  id="$(run aws athena start-query-execution --work-group "$ATHENA_WG" \
        --query-execution-context "Database=$GLUE_DATABASE" \
        --query-string "file://$rendered" --query QueryExecutionId --output text | tail -n 1)"
  [[ "$DRY_RUN" == "1" ]] && return 0
  local state
  while true; do
    state="$(aws athena get-query-execution --query-execution-id "$id" \
             --query QueryExecution.Status.State --output text)"
    case "$state" in SUCCEEDED|FAILED|CANCELLED) break ;; esac
    sleep 2
  done
  aws athena get-query-execution --query-execution-id "$id" --output text \
    --query 'QueryExecution.[Status.State,Statistics.DataScannedInBytes,Statistics.TotalExecutionTimeInMillis,Status.StateChangeReason]' \
    | awk -F'\t' '{printf "   state=%s scanned_bytes=%s time_ms=%s %s\n", $1, $2, $3, ($4 == "None" ? "" : $4)}'
  [[ "$state" == "SUCCEEDED" ]] || return 1
  if [[ "$file" == sql/checks/* ]]; then
    aws athena get-query-results --query-execution-id "$id" --output text \
      --query 'ResultSet.Rows[].Data[].VarCharValue' | sed 's/^/   /'
  fi
}

# 1. Workgroup
render infra/athena/workgroup.template.json "$RENDER_DIR/workgroup.json"
if aws athena get-work-group --work-group "$ATHENA_WG" >/dev/null 2>&1; then
  echo "Workgroup $ATHENA_WG already exists - creation skipped (settings unchanged)."
else
  run aws athena create-work-group --name "$ATHENA_WG" \
    --configuration "file://$RENDER_DIR/workgroup.json" \
    --description "RAG assistant monitoring (synthetic data)" \
    --tags "Key=Project,Value=$PROJECT"
fi

# 2. Tables (DDL)
for f in sql/0*_create_table_*.sql; do athena_run "$f"; done

# 3. Acceptance checks
for f in sql/checks/*.sql; do athena_run "$f"; done
