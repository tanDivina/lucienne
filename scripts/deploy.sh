#!/usr/bin/env bash
# Deploy Lucienne: CloudFormation stack + Lambda code upload.
# Usage: scripts/deploy.sh [stack-name]
set -euo pipefail
cd "$(dirname "$0")/.."

STACK="${1:-lucienne}"
REGION="${AWS_REGION:-us-east-1}"
REPORT_FROM="${REPORT_FROM:-dorien.vda@gmail.com}"
ALLOWED="${ALLOWED_REPORT_RECIPIENTS:-$REPORT_FROM}"
ORIGINATION="${ORIGINATION_IDENTITY:-}"

echo "==> Deploying stack '$STACK' in $REGION"
aws cloudformation deploy \
  --region "$REGION" \
  --stack-name "$STACK" \
  --template-file infra/template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    ReportFrom="$REPORT_FROM" \
    AllowedReportRecipients="$ALLOWED" \
    OriginationIdentity="$ORIGINATION" \
    PsiApiKey="${PSI_API_KEY:-}"

echo "==> Packaging Lambda code"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
cp -R src/. "$BUILD/"
(cd "$BUILD" && zip -qr code.zip . -x 'code.zip' '*.pyc' '__pycache__/*')

FN="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text)"
aws lambda update-function-code --region "$REGION" \
  --function-name "$FN" --zip-file "fileb://$BUILD/code.zip" --no-cli-pager >/dev/null
aws lambda wait function-updated --region "$REGION" --function-name "$FN"

echo "==> Done"
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs" --output table
