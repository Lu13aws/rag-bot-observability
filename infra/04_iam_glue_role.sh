#!/usr/bin/env bash
# Step 3.3: IAM role for the Glue job (least privilege).
# - AWSGlueServiceRole: Glue core permissions incl. its CloudWatch log groups
# - Inline policy: read raw/ and scripts/, write processed/ in the project bucket only
source "$(dirname "$0")/lib.sh"

if aws iam get-role --role-name "$GLUE_ROLE" >/dev/null 2>&1; then
  echo "Role $GLUE_ROLE already exists - creation skipped."
else
  run aws iam create-role --role-name "$GLUE_ROLE" \
    --assume-role-policy-document "file://infra/iam/glue-trust-policy.json" \
    --tags "Key=Project,Value=$PROJECT"
fi

run aws iam attach-role-policy --role-name "$GLUE_ROLE" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"

render infra/iam/glue-s3-policy.template.json "$RENDER_DIR/glue-s3-policy.json"
run aws iam put-role-policy --role-name "$GLUE_ROLE" \
  --policy-name "S3-${PROJECT}" \
  --policy-document "file://$RENDER_DIR/glue-s3-policy.json"
