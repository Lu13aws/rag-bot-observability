#!/usr/bin/env bash
# Read-only inventory of common cost drivers in the given regions.
# Only list/describe calls; nothing is changed, stopped or deleted.
# Usage: bash infra/11_inventory.sh [region ...]   (default: eu-central-1 us-east-1)
set -uo pipefail  # no -e: a service that is not available must not stop the report

REGIONS=("${@:-eu-central-1 us-east-1}")
# shellcheck disable=SC2206
REGIONS=(${REGIONS[*]})

section() { printf '\n--- %s\n' "$1"; }
q() { "$@" 2>&1 | sed '/^$/d' || true; }

for R in "${REGIONS[@]}"; do
  echo; echo "=================== $R ==================="
  section "EC2 instances (id, type, state, name)"
  q aws ec2 describe-instances --region "$R" --output text \
    --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`]|[0].Value]'
  section "EBS volumes (id, GB, type, state)"
  q aws ec2 describe-volumes --region "$R" --output text --query 'Volumes[].[VolumeId,Size,VolumeType,State]'
  section "Elastic IPs (ip, allocation, associated instance)"
  q aws ec2 describe-addresses --region "$R" --output text --query 'Addresses[].[PublicIp,AllocationId,InstanceId]'
  section "NAT gateways (id, state, vpc)"
  q aws ec2 describe-nat-gateways --region "$R" --output text --query 'NatGateways[?State!=`deleted`].[NatGatewayId,State,VpcId]'
  section "Load balancers v2 (name, type, state)"
  q aws elbv2 describe-load-balancers --region "$R" --output text --query 'LoadBalancers[].[LoadBalancerName,Type,State.Code]'
  section "Classic load balancers"
  q aws elb describe-load-balancers --region "$R" --output text --query 'LoadBalancerDescriptions[].LoadBalancerName'
  section "RDS instances (id, class, engine, status)"
  q aws rds describe-db-instances --region "$R" --output text --query 'DBInstances[].[DBInstanceIdentifier,DBInstanceClass,Engine,DBInstanceStatus]'
  section "RDS/Aurora clusters (id, engine, status)"
  q aws rds describe-db-clusters --region "$R" --output text --query 'DBClusters[].[DBClusterIdentifier,Engine,Status]'
  section "OpenSearch domains"
  q aws opensearch list-domain-names --region "$R" --output text --query 'DomainNames[].DomainName'
  section "OpenSearch Serverless collections (name, type, status)"
  q aws opensearchserverless list-collections --region "$R" --output text --query 'collectionSummaries[].[name,status]'
  section "Bedrock provisioned throughput"
  q aws bedrock list-provisioned-model-throughputs --region "$R" --output text --query 'provisionedModelSummaries[].[provisionedModelName,status]'
  section "Bedrock knowledge bases (name, status)"
  q aws bedrock-agent list-knowledge-bases --region "$R" --output text --query 'knowledgeBaseSummaries[].[name,status]'
  section "SageMaker endpoints (name, status)"
  q aws sagemaker list-endpoints --region "$R" --output text --query 'Endpoints[].[EndpointName,EndpointStatus]'
done

echo; echo "=================== S3 (global list, bucket region) ==================="
for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do
  loc="$(aws s3api get-bucket-location --bucket "$b" --query LocationConstraint --output text 2>/dev/null)"
  [[ "$loc" == "None" ]] && loc="us-east-1"
  echo "$b  ($loc)"
done
