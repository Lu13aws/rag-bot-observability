#!/usr/bin/env bash
# Step S2.3.1: Athena workgroup, table definitions and acceptance checks.
# - Workgroup: results in s3://<bucket>/athena-results/ (SSE-S3), settings
#   enforced, scan limit 100 MB per query, tag Project (NFR-03).
# - Tables: sql/01_*.sql and sql/02_*.sql (CREATE ... IF NOT EXISTS).
# - Checks: sql/checks/*.sql, results printed as a table.
source "$(dirname "$0")/lib.sh"   # provides ATHENA_WG and athena_run
: "${GLUE_DATABASE:?}"

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
