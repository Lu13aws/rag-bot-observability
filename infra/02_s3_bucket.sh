#!/usr/bin/env bash
# Step 3.1: project bucket with prefixes raw/, processed/, reference/, scripts/.
# Private (all public access blocked), ACLs disabled, SSE-S3 with Bucket Key,
# versioning off (default for new buckets). Settings are re-applied on every run.
source "$(dirname "$0")/lib.sh"

if aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  echo "Bucket $BUCKET already exists - creation skipped."
else
  run aws s3api create-bucket --bucket "$BUCKET" \
    --create-bucket-configuration "LocationConstraint=$AWS_REGION"
fi

run aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

run aws s3api put-bucket-ownership-controls --bucket "$BUCKET" \
  --ownership-controls "Rules=[{ObjectOwnership=BucketOwnerEnforced}]"

run aws s3api put-bucket-encryption --bucket "$BUCKET" \
  --server-side-encryption-configuration "file://infra/s3/encryption.json"

run aws s3api put-bucket-tagging --bucket "$BUCKET" \
  --tagging "TagSet=[{Key=Project,Value=$PROJECT}]"
