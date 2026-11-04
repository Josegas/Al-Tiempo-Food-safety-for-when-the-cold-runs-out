#!/usr/bin/env bash
# Creates an access key for the IAM user "al-tiempo-dev" and saves it in the AWS CLI profile
# "al-tiempo". The secret is never printed. Run once, with an admin profile:
#   ADMIN_PROFILE=default ./scripts/setup_dev_profile.sh
set -euo pipefail
ADMIN_PROFILE="${ADMIN_PROFILE:-default}"
USER_NAME="al-tiempo-dev"
PROFILE="al-tiempo"
REGION="us-east-1"

count=$(aws iam list-access-keys --user-name "$USER_NAME" --profile "$ADMIN_PROFILE" \
  --query 'length(AccessKeyMetadata)' --output text)
if [ "$count" -ge 1 ]; then
  echo "El usuario $USER_NAME ya tiene $count llave(s). Bórrala(s) antes si quieres crear otra." >&2
  exit 1
fi

read -r AK SK < <(aws iam create-access-key --user-name "$USER_NAME" --profile "$ADMIN_PROFILE" \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
aws configure set aws_access_key_id "$AK" --profile "$PROFILE"
aws configure set aws_secret_access_key "$SK" --profile "$PROFILE"
aws configure set region "$REGION" --profile "$PROFILE"
unset AK SK

echo "Esperando a que IAM propague la llave nueva..."
for _ in $(seq 1 12); do
  if arn=$(aws sts get-caller-identity --profile "$PROFILE" --query Arn --output text 2>/dev/null); then
    echo "Listo. Perfil '$PROFILE' -> $arn"
    exit 0
  fi
  sleep 5
done
echo "La llave se creó pero aún no responde; intenta: aws sts get-caller-identity --profile $PROFILE" >&2
exit 1
