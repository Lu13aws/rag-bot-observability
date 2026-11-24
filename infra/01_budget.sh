#!/usr/bin/env bash
# Step 3.0b: monthly cost budget for this project only (NFR-03).
# - Counts only costs tagged Project=<PROJECT> (cost allocation tag), so other
#   workloads in the same account do not trigger the alerts.
# - Alerts: 20 USD actual, 40 USD actual, 100 % forecasted. Free of charge
#   (see research/notes/aws-pricing-2026-11.md).
# - Creates the budget, or updates it if it already exists.
source "$(dirname "$0")/lib.sh"
: "${ALERT_EMAIL:?Set ALERT_EMAIL in infra/config.env}"

ACCOUNT_ID="$(account_id)"
BUDGET_NAME="${PROJECT}-monthly"

# The tag key must be active as a cost allocation tag before a tag filter
# counts anything. Takes effect for new costs, up to 24 hours delay.
run aws ce update-cost-allocation-tags-status --region us-east-1 \
  --cost-allocation-tags-status "TagKey=Project,Status=Active"

render infra/budget/budget.template.json "$RENDER_DIR/budget.json"
render infra/budget/notifications.template.json "$RENDER_DIR/notifications.json"

if aws budgets describe-budget --account-id "$ACCOUNT_ID" --budget-name "$BUDGET_NAME" >/dev/null 2>&1; then
  # Updates amount and filter; existing notifications are kept
  run aws budgets update-budget --account-id "$ACCOUNT_ID" \
    --new-budget "file://$RENDER_DIR/budget.json"
else
  run aws budgets create-budget \
    --account-id "$ACCOUNT_ID" \
    --budget "file://$RENDER_DIR/budget.json" \
    --notifications-with-subscribers "file://$RENDER_DIR/notifications.json"
fi

if [[ "$DRY_RUN" != "1" ]]; then
  aws budgets describe-notifications-for-budget --account-id "$ACCOUNT_ID" \
    --budget-name "$BUDGET_NAME" --output table
fi
