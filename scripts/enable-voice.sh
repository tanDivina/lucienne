#!/usr/bin/env bash
# Let Lucienne understand WhatsApp voice notes on an already deployed stack, without
# re-running deploy.sh (which resets its parameters): adds the Transcribe and
# GetWhatsAppMessageMedia permissions to her role, then uploads the code.
set -euo pipefail
cd "$(dirname "$0")/.."
STACK="${1:-lucienne}"
REGION="${AWS_REGION:-us-east-1}"
FN="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text)"
ROLE="$(aws lambda get-function-configuration --region "$REGION" --function-name "$FN" --query Role --output text)"
ROLE="${ROLE##*/}"

aws iam put-role-policy --role-name "$ROLE" --policy-name lucienne-voice --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "social-messaging:GetWhatsAppMessageMedia", "Resource": "*"},
    {"Effect": "Allow", "Action": ["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob", "transcribe:DeleteTranscriptionJob"], "Resource": "*"}
  ]
}'
echo "role $ROLE ready"

BUILD="$(mktemp -d)"; trap 'rm -rf "$BUILD"' EXIT
cp -R src/. "$BUILD/"
(cd "$BUILD" && zip -qr code.zip . -x 'code.zip' '*.pyc' '__pycache__/*')
aws lambda update-function-code --region "$REGION" --function-name "$FN" \
  --zip-file "fileb://$BUILD/code.zip" --no-cli-pager --query LastModified --output text
aws lambda wait function-updated --region "$REGION" --function-name "$FN"
echo "deployed"
