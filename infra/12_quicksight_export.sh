#!/usr/bin/env bash
# S5.2.1: read-only export of the QuickSight assets before the trial is
# cancelled (the cancellation deletes all dashboards).
# Exports into quicksight/export/:
#   dashboards/<id>.json  describe-dashboard-definition
#   analyses/<id>.json    describe-analysis-definition
#   datasets/<id>.json    describe-data-set (incl. row-level security config)
#   datasets/<id>.refresh-schedules.json  list-refresh-schedules
#   groups.txt            group names only (no memberships, no user names)
# - Read-only: only list-* and describe-* calls; nothing is changed.
# - Privacy: account ID -> <account-id>, e-mail addresses -> <email>,
#   bucket name -> <bucket>. The script fails if any of them remains.
# - Review the exported files before committing them.
# Usage: bash infra/12_quicksight_export.sh   (DRY_RUN=1: print commands only)
source "$(dirname "$0")/lib.sh"

ACCOUNT_ID="$(account_id)"
OUT="quicksight/export"
QS=(aws quicksight --aws-account-id "$ACCOUNT_ID")
EMAIL_RE='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
ACCOUNT_RE='(^|[^0-9])[0-9]{12}([^0-9]|$)'

# scrub <file>: mask account ID, e-mail addresses and bucket name in place
scrub() {
  sed -i -E -e "s/${ACCOUNT_ID}/<account-id>/g" -e "s/${EMAIL_RE}/<email>/g" \
            -e "s/${BUCKET}/<bucket>/g" "$1"
}

# export_json <file> <aws args...>: run a read-only call, store and scrub it
export_json() {
  local file="$1"; shift
  if [[ "$DRY_RUN" == "1" ]]; then run "$@"; return 0; fi
  run "$@" --output json > "$file"
  scrub "$file"
}

# list_ids <jmespath> <aws args...>: IDs from a list-* call (not in dry run)
list_ids() {
  local query="$1"; shift
  if [[ "$DRY_RUN" == "1" ]]; then run "$@"; echo "<id>"; return 0; fi
  "$@" --query "$query" --output text | tr '\t' '\n' | tr -d '\r' | sed '/^$/d'
}

mkdir -p "$OUT/dashboards" "$OUT/analyses" "$OUT/datasets"

echo "== Dashboards"
for id in $(list_ids 'DashboardSummaryList[].DashboardId' "${QS[@]}" list-dashboards); do
  export_json "$OUT/dashboards/$id.json" "${QS[@]}" describe-dashboard-definition --dashboard-id "$id"
done

echo "== Analyses"
for id in $(list_ids 'AnalysisSummaryList[?Status!=`DELETED`].AnalysisId' "${QS[@]}" list-analyses); do
  export_json "$OUT/analyses/$id.json" "${QS[@]}" describe-analysis-definition --analysis-id "$id"
done

echo "== Datasets"
for id in $(list_ids 'DataSetSummaries[].DataSetId' "${QS[@]}" list-data-sets); do
  export_json "$OUT/datasets/$id.json" "${QS[@]}" describe-data-set --data-set-id "$id"
  export_json "$OUT/datasets/$id.refresh-schedules.json" "${QS[@]}" list-refresh-schedules --data-set-id "$id"
done

echo "== Groups (names only)"
if [[ "$DRY_RUN" == "1" ]]; then
  run "${QS[@]}" list-groups --namespace default --query 'GroupList[].GroupName' --output text
else
  run "${QS[@]}" list-groups --namespace default --query 'GroupList[].GroupName' --output text \
    | tr '\t' '\n' | tr -d '\r' > "$OUT/groups.txt"
fi

[[ "$DRY_RUN" == "1" ]] && exit 0

echo
echo "== Privacy check"
if grep -rlE "$ACCOUNT_RE|$EMAIL_RE|$BUCKET" "$OUT"; then
  echo "FAILED: the files above still contain an account ID, e-mail address or bucket name." >&2
  exit 1
fi
echo "Exported $(find "$OUT" -type f | wc -l) files to $OUT/ - review them before committing."
