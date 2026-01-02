#!/bin/bash
# Cloud Functions 배포 스크립트

set -e

# 프로젝트 ID 확인
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ 프로젝트가 설정되지 않았습니다."
    echo "먼저 다음 명령어를 실행하세요:"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

FUNCTION_NAME="pipeline_function"
REGION="asia-northeast3"
RUNTIME="python39"
ENTRY_POINT="main"
TIMEOUT="3600s"
MEMORY="512MB"

# 환경 변수
GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-kakao-webtoon-raw}"
BIGQUERY_PROJECT_ID="${BIGQUERY_PROJECT_ID:-$PROJECT_ID}"
BIGQUERY_DATASET_ID="${BIGQUERY_DATASET_ID:-kakao_webtoon}"

echo "=== Cloud Functions 배포 ==="
echo "프로젝트: $PROJECT_ID"
echo "함수명: $FUNCTION_NAME"
echo "리전: $REGION"
echo ""

# 배포 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 상위 디렉토리의 src 디렉토리를 현재 디렉토리로 복사 (Cloud Functions에서 사용)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -d "$PROJECT_ROOT/src" ]; then
    echo "src 디렉토리 복사 중..."
    cp -r "$PROJECT_ROOT/src" . || {
        echo "⚠️  src 디렉토리 복사 실패, 심볼릭 링크 시도..."
        ln -sf "$PROJECT_ROOT/src" . || {
            echo "❌ src 디렉토리 준비 실패"
            exit 1
        }
    }
fi

# Cloud Functions 배포
echo "Cloud Functions 배포 중..."
gcloud functions deploy "$FUNCTION_NAME" \
    --gen2 \
    --runtime="$RUNTIME" \
    --region="$REGION" \
    --source=. \
    --entry-point="$ENTRY_POINT" \
    --trigger-http \
    --allow-unauthenticated \
    --timeout="$TIMEOUT" \
    --memory="$MEMORY" \
    --set-env-vars "GCS_BUCKET_NAME=$GCS_BUCKET_NAME,BIGQUERY_PROJECT_ID=$BIGQUERY_PROJECT_ID,BIGQUERY_DATASET_ID=$BIGQUERY_DATASET_ID,DATA_FORMAT=jsonl" \
    --service-account="webtoon-collector@${PROJECT_ID}.iam.gserviceaccount.com" \
    --max-instances=1

echo ""
echo "✅ 배포 완료!"
echo ""
echo "함수 URL 확인:"
gcloud functions describe "$FUNCTION_NAME" --gen2 --region="$REGION" --format="value(serviceConfig.uri)"

