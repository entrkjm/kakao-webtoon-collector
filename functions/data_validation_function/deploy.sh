#!/bin/bash
# 데이터 검증 Cloud Function 배포 스크립트

set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ 프로젝트가 설정되지 않았습니다."
    echo "먼저 다음 명령어를 실행하세요:"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

REGION="${GCP_REGION:-asia-northeast3}"
FUNCTION_NAME="data-validation-function"
SERVICE_ACCOUNT="webtoon-collector@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== 데이터 검증 Cloud Function 배포 ==="
echo "프로젝트: $PROJECT_ID"
echo "함수 이름: $FUNCTION_NAME"
echo ""

cd "$(dirname "$0")"

# 환경 변수 설정
export BIGQUERY_PROJECT_ID="$PROJECT_ID"
export BIGQUERY_DATASET_ID="kakao_webtoon"
export MIN_EXPECTED_RECORDS="${MIN_EXPECTED_RECORDS:-500}"  # 기본값: 500, 환경 변수로 오버라이드 가능
export NOTIFICATION_CHANNEL_EMAIL="${NOTIFICATION_CHANNEL_EMAIL:-}"

# Cloud Function 배포
echo "Cloud Function 배포 중..."
gcloud functions deploy "$FUNCTION_NAME" \
    --gen2 \
    --runtime=python311 \
    --region="$REGION" \
    --source=. \
    --entry-point=main \
    --trigger-http \
    --allow-unauthenticated \
    --service-account="$SERVICE_ACCOUNT" \
    --timeout=540s \
    --memory=256MB \
    --max-instances=1 \
    --set-env-vars="BIGQUERY_PROJECT_ID=$BIGQUERY_PROJECT_ID,BIGQUERY_DATASET_ID=$BIGQUERY_DATASET_ID,MIN_EXPECTED_RECORDS=$MIN_EXPECTED_RECORDS,NOTIFICATION_CHANNEL_EMAIL=$NOTIFICATION_CHANNEL_EMAIL" \
    2>&1 | grep -v "Waiting on"

echo ""
echo "✅ 배포 완료!"
echo ""
echo "함수 URL 확인:"
gcloud functions describe "$FUNCTION_NAME" \
    --gen2 \
    --region="$REGION" \
    --format="value(serviceConfig.uri)" \
    2>&1 | grep -v "Waiting on"

