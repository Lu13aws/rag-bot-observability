#!/usr/bin/env bash
# Step S2.3.2: KPI reference views in Athena (CREATE OR REPLACE VIEW).
# Runs sql/views/*.sql in file order (base view first, v_kpi_all last).
# DDL only: no data is scanned. Compare the results afterwards with
#   python ingestion/compare_kpis.py
source "$(dirname "$0")/lib.sh"
: "${GLUE_DATABASE:?}"

for f in sql/views/*.sql; do
  athena_run "$f"
done
