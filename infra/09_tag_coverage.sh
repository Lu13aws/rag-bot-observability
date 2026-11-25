#!/usr/bin/env bash
# Step S5.1.4: read-only check that every cost-relevant project resource carries
# the tag Project=<PROJECT>, so the tag-filtered budget (NFR-03) sees its cost.
# - Part 1: expected resources, tag read per service
# - Part 2: discovery of resources named like the project but missing the tag
# - Part 3: cost allocation tag status (Cost Explorer API, about 0.01 USD)
# Exit code 1 if a cost-relevant resource is untagged. Nothing is changed.
source "$(dirname "$0")/lib.sh"
: "${GLUE_DATABASE:?}"

ACCOUNT_ID="$(account_id)"
GLUE_JOB_ARN="arn:aws:glue:${AWS_REGION}:${ACCOUNT_ID}:job/${GLUE_JOB}"
GLUE_DB_ARN="arn:aws:glue:${AWS_REGION}:${ACCOUNT_ID}:database/${GLUE_DATABASE}"
WG_ARN="arn:aws:athena:${AWS_REGION}:${ACCOUNT_ID}:workgroup/${ATHENA_WG}"
MISSING=0

# check <label> <cost-relevant yes|no> <command printing the Project tag value>
check() {
  local label="$1" relevant="$2"; shift 2
  local value
  value="$("$@" 2>/dev/null | tr -d '\r')"
  if [[ "$value" == "$PROJECT" ]]; then
    printf '  %-34s tagged     (cost-relevant: %s)\n' "$label" "$relevant"
  else
    printf '  %-34s NOT TAGGED (cost-relevant: %s)\n' "$label" "$relevant"
    # if-statement, not "[[ ]] &&": a false test would end the script under set -e
    if [[ "$relevant" == "yes" ]]; then MISSING=$((MISSING + 1)); fi
  fi
}

echo "== 1. Expected project resources"
check "S3 bucket"              yes aws s3api get-bucket-tagging --bucket "$BUCKET" \
  --query "TagSet[?Key=='Project'].Value | [0]" --output text
check "IAM role (Glue)"        no  aws iam list-role-tags --role-name "$GLUE_ROLE" \
  --query "Tags[?Key=='Project'].Value | [0]" --output text
check "Glue job"               yes aws glue get-tags --resource-arn "$GLUE_JOB_ARN" \
  --query "Tags.Project" --output text
check "Glue database"          no  aws glue get-tags --resource-arn "$GLUE_DB_ARN" \
  --query "Tags.Project" --output text
check "Athena workgroup"       yes aws athena list-tags-for-resource --resource-arn "$WG_ARN" \
  --query "Tags[?Key=='Project'].Value | [0]" --output text
check "Budget"                 no  aws budgets list-tags-for-resource \
  --resource-arn "arn:aws:budgets::${ACCOUNT_ID}:budget/${PROJECT}-monthly" \
  --query "ResourceTags[?Key=='Project'].Value | [0]" --output text

echo
echo "== 2. Discovery: resources named like the project"
for b in $(aws s3api list-buckets --query "Buckets[?starts_with(Name, 'rag-bot-obs-')].Name" --output text); do
  check "S3 $b" yes aws s3api get-bucket-tagging --bucket "$b" \
    --query "TagSet[?Key=='Project'].Value | [0]" --output text
done
for j in $(aws glue list-jobs --query "JobNames[?contains(@, 'rag-query')]" --output text); do
  check "Glue job $j" yes aws glue get-tags --resource-arn "arn:aws:glue:${AWS_REGION}:${ACCOUNT_ID}:job/$j" \
    --query "Tags.Project" --output text
done
for w in $(aws athena list-work-groups --query "WorkGroups[?contains(Name, 'rag-bot')].Name" --output text); do
  check "Athena workgroup $w" yes aws athena list-tags-for-resource \
    --resource-arn "arn:aws:athena:${AWS_REGION}:${ACCOUNT_ID}:workgroup/$w" \
    --query "Tags[?Key=='Project'].Value | [0]" --output text
done

echo
echo "== 3. Cost allocation tag (Cost Explorer API)"
aws ce list-cost-allocation-tags --region us-east-1 --tag-keys Project \
  --query 'CostAllocationTags[].[TagKey,Status]' --output text | sed 's/^/  /'

echo
echo "Untagged cost-relevant resources: $MISSING"
exit $(( MISSING > 0 ? 1 : 0 ))
