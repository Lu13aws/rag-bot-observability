#!/usr/bin/env bash
# Step 3.0a: show which AWS identity and permissions the scripts will use.
# Read-only. The output contains the account ID: do not paste it into the repo.
source "$(dirname "$0")/lib.sh"

aws --version
aws configure list
aws sts get-caller-identity --output table

ARN="$(aws sts get-caller-identity --query Arn --output text)"
if [[ "$ARN" == *":user/"* ]]; then
  USER_NAME="${ARN##*/}"
  echo "== Attached user policies";  aws iam list-attached-user-policies --user-name "$USER_NAME" --output table
  echo "== Inline user policies";    aws iam list-user-policies --user-name "$USER_NAME" --output table
  for g in $(aws iam list-groups-for-user --user-name "$USER_NAME" --query 'Groups[].GroupName' --output text); do
    echo "== Group $g";              aws iam list-attached-group-policies --group-name "$g" --output table
  done
fi
