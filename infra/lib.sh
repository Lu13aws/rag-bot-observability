#!/usr/bin/env bash
# Shared settings and helpers for the infra scripts. Sourced, not run directly.
#
# - Reads infra/config.env (git-ignored).
# - Reads the AWS account ID at runtime only; it is never written to the repo.
# - DRY_RUN=1 prints every AWS command that changes something without running it.
set -euo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$INFRA_DIR")"
cd "$REPO_DIR"  # all file:// paths below are relative to the repo root

CONFIG="infra/config.env"
if [[ ! -f "$CONFIG" ]]; then
  echo "Missing $CONFIG - copy infra/config.env.example and fill it in." >&2
  exit 1
fi
# Strip a UTF-8 BOM and Windows line endings (e.g. if edited with PowerShell)
# shellcheck disable=SC1090
source <(sed -e '1s/^\xEF\xBB\xBF//' -e 's/\r$//' "$CONFIG")
: "${AWS_REGION:?}" "${PROJECT:?}" "${BUCKET:?}"
if [[ "$BUCKET" == *CHANGE-ME* ]]; then
  echo "Set BUCKET in $CONFIG" >&2
  exit 1
fi
export AWS_REGION AWS_DEFAULT_REGION="$AWS_REGION"
# Git Bash on Windows rewrites arguments starting with "/" into Windows paths
# (e.g. the log group /aws-glue/jobs/output). Disable that for all AWS calls.
export MSYS_NO_PATHCONV=1

DRY_RUN="${DRY_RUN:-0}"
GLUE_ROLE="GlueETLRole-${PROJECT}"
GLUE_JOB="rag-query-log-json-to-parquet"
RENDER_DIR="infra/.rendered"  # git-ignored; holds templates with real values
mkdir -p "$RENDER_DIR"

# Print a command (to stderr, so callers can capture stdout), then run it
# (unless DRY_RUN=1).
run() {
  echo "+ $*" >&2
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  "$@"
}

account_id() {
  aws sts get-caller-identity --query Account --output text
}

# render <template> <output>: replace __PLACEHOLDERS__ with values from config.env
render() {
  sed -e "s|__BUCKET__|${BUCKET}|g" \
      -e "s|__PROJECT__|${PROJECT}|g" \
      -e "s|__EMAIL__|${ALERT_EMAIL:-}|g" \
      -e "s|__BUDGET_USD__|${BUDGET_USD:-50}|g" \
      -e "s|__ROLE_ARN__|${ROLE_ARN:-}|g" \
      -e "s|__GLUE_VERSION__|${GLUE_VERSION:-5.0}|g" \
      "$1" > "$2"
}
