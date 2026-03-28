#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Build, push, and deploy the report generator to AWS Lambda
# Usage: ./deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
AWS_REGION="us-east-1"
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="realai-report-generator"
LAMBDA_FUNCTION="realai-report-generator"
LAMBDA_ROLE="realai-report-generator-role"
S3_BUCKET="realai-report-gen-tmp"
IMAGE_TAG="latest"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

echo "════════════════════════════════════════════"
echo " Deploying to AWS Lambda"
echo " Account : $AWS_ACCOUNT"
echo " Region  : $AWS_REGION"
echo " Function: $LAMBDA_FUNCTION"
echo "════════════════════════════════════════════"

# ── 1. Ensure S3 bucket exists ────────────────────────────────────────────────
echo ""
echo "▶ Step 1/6 — S3 bucket"
if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
  echo "  ✓ Bucket $S3_BUCKET already exists"
else
  aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION"
  # Auto-delete report objects after 1 day
  aws s3api put-bucket-lifecycle-configuration --bucket "$S3_BUCKET" \
    --lifecycle-configuration '{
      "Rules":[{"ID":"expire-reports","Status":"Enabled",
        "Filter":{"Prefix":"reports/"},
        "Expiration":{"Days":1}}]}'
  echo "  ✓ Bucket $S3_BUCKET created (reports expire after 1 day)"
fi

# ── 2. IAM role ───────────────────────────────────────────────────────────────
echo ""
echo "▶ Step 2/6 — IAM role"
TRUST_POLICY='{
  "Version":"2012-10-17",
  "Statement":[{
    "Effect":"Allow",
    "Principal":{"Service":"lambda.amazonaws.com"},
    "Action":"sts:AssumeRole"
  }]
}'

if aws iam get-role --role-name "$LAMBDA_ROLE" 2>/dev/null | grep -q RoleId; then
  echo "  ✓ Role $LAMBDA_ROLE already exists"
else
  aws iam create-role --role-name "$LAMBDA_ROLE" \
    --assume-role-policy-document "$TRUST_POLICY" > /dev/null
  echo "  ✓ Role $LAMBDA_ROLE created"
fi

ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE" --query Role.Arn --output text)

# Attach required policies
for POLICY in \
  "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
  "arn:aws:iam::aws:policy/AmazonS3FullAccess" \
  "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"; do
  aws iam attach-role-policy --role-name "$LAMBDA_ROLE" --policy-arn "$POLICY" 2>/dev/null || true
done
echo "  ✓ Policies attached (Lambda execution, S3, Bedrock)"

# ── 3. ECR repository ─────────────────────────────────────────────────────────
echo ""
echo "▶ Step 3/6 — ECR repository"
if aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" 2>/dev/null | grep -q repositoryUri; then
  echo "  ✓ Repository $ECR_REPO already exists"
else
  aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION" > /dev/null
  echo "  ✓ Repository $ECR_REPO created"
fi

# ── 4. Build & push Docker image ──────────────────────────────────────────────
echo ""
echo "▶ Step 4/6 — Build & push Docker image"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build --platform linux/amd64 -t "${ECR_REPO}:${IMAGE_TAG}" .
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"
echo "  ✓ Image pushed: ${ECR_URI}:${IMAGE_TAG}"

# ── 5. Create or update Lambda function ───────────────────────────────────────
echo ""
echo "▶ Step 5/6 — Lambda function"

ENV_VARS="Variables={REPORT_S3_BUCKET=${S3_BUCKET},AWS_REGION_NAME=${AWS_REGION}}"

if aws lambda get-function --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION" 2>/dev/null | grep -q FunctionArn; then
  echo "  Updating existing function..."
  aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION" \
    --image-uri "${ECR_URI}:${IMAGE_TAG}" \
    --region "$AWS_REGION" > /dev/null
  aws lambda wait function-updated --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"
  aws lambda update-function-configuration \
    --function-name "$LAMBDA_FUNCTION" \
    --timeout 300 \
    --memory-size 1024 \
    --environment "$ENV_VARS" \
    --region "$AWS_REGION" > /dev/null
  echo "  ✓ Function updated"
else
  echo "  Creating new function (waiting for IAM role to propagate)..."
  sleep 10
  aws lambda create-function \
    --function-name "$LAMBDA_FUNCTION" \
    --package-type Image \
    --code "ImageUri=${ECR_URI}:${IMAGE_TAG}" \
    --role "$ROLE_ARN" \
    --timeout 300 \
    --memory-size 1024 \
    --environment "$ENV_VARS" \
    --region "$AWS_REGION" > /dev/null
  aws lambda wait function-active --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"
  echo "  ✓ Function created"
fi

# ── 6. Function URL ───────────────────────────────────────────────────────────
echo ""
echo "▶ Step 6/6 — Function URL"
EXISTING_URL=$(aws lambda get-function-url-config \
  --function-name "$LAMBDA_FUNCTION" \
  --region "$AWS_REGION" \
  --query FunctionUrl --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_URL" ]; then
  FUNCTION_URL="$EXISTING_URL"
  echo "  ✓ Function URL already configured"
else
  FUNCTION_URL=$(aws lambda create-function-url-config \
    --function-name "$LAMBDA_FUNCTION" \
    --auth-type AWS_IAM \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["POST","GET"],"AllowHeaders":["*","authorization","x-amz-security-token","x-amz-date"]}' \
    --region "$AWS_REGION" \
    --query FunctionUrl --output text)
  echo "  ✓ Function URL created (IAM auth — not public)"
fi

echo ""
echo "════════════════════════════════════════════"
echo " ✅ Deployment complete!"
echo "════════════════════════════════════════════"
echo ""
echo " Endpoint : ${FUNCTION_URL}"
echo " Health   : ${FUNCTION_URL}health"
echo ""
echo " Generate a report (requires AWS SigV4 — use awscurl or boto3):"
echo "   awscurl --service lambda --region ${AWS_REGION} \\"
echo "     -X POST ${FUNCTION_URL}generate-report \\"
echo '     -F "rent_roll=@data/rent_roll.pdf" \'
echo '     -F "financials=@data/t12.pdf"'
echo ""
echo " Response: {\"download_url\": \"<presigned S3 URL>\", \"expires_in_seconds\": 900}"
echo "════════════════════════════════════════════"
