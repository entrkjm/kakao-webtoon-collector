#!/bin/bash
# GCP 인프라 사전 준비 스크립트

set -e

# 프로젝트 ID 확인
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ 프로젝트가 설정되지 않았습니다."
    echo "먼저 다음 명령어를 실행하세요:"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "=== GCP 인프라 사전 준비 ==="
echo "프로젝트: $PROJECT_ID"
echo ""

# 1. 필요한 API 활성화
echo "1. 필요한 API 활성화 중..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
echo "✅ API 활성화 완료"
echo ""

# 2. GCS 버킷 생성
BUCKET_NAME="${GCS_BUCKET_NAME:-kakao-webtoon-raw}"
REGION="asia-northeast3"

echo "2. GCS 버킷 생성 중..."
if gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
    echo "⚠️  버킷이 이미 존재합니다: gs://${BUCKET_NAME}"
else
    gsutil mb -l "${REGION}" "gs://${BUCKET_NAME}"
    echo "✅ 버킷 생성 완료: gs://${BUCKET_NAME}"
fi
echo ""

# 3. BigQuery 데이터셋 생성
DATASET_ID="${BIGQUERY_DATASET_ID:-kakao_webtoon}"

echo "3. BigQuery 데이터셋 생성 중..."
if bq ls -d "${PROJECT_ID}:${DATASET_ID}" >/dev/null 2>&1; then
    echo "⚠️  데이터셋이 이미 존재합니다: ${PROJECT_ID}:${DATASET_ID}"
else
    bq mk --dataset --location="${REGION}" "${PROJECT_ID}:${DATASET_ID}"
    echo "✅ 데이터셋 생성 완료: ${PROJECT_ID}:${DATASET_ID}"
fi
echo ""

# 4. BigQuery 테이블 생성
echo "4. BigQuery 테이블 생성 중..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/setup_bigquery.sql"

if [ -f "${SQL_FILE}" ]; then
    # 프로젝트 ID를 실제 값으로 치환
    sed "s/kakao-webtoon-collector/${PROJECT_ID}/g" "${SQL_FILE}" | bq query --use_legacy_sql=false
    echo "✅ 테이블 생성 완료"
else
    echo "⚠️  SQL 파일을 찾을 수 없습니다: ${SQL_FILE}"
    echo "수동으로 BigQuery 콘솔에서 테이블을 생성하세요."
fi
echo ""

# 5. 서비스 계정 생성
SERVICE_ACCOUNT_NAME="webtoon-collector"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "5. 서비스 계정 생성 중..."
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" >/dev/null 2>&1; then
    echo "⚠️  서비스 계정이 이미 존재합니다: ${SERVICE_ACCOUNT_EMAIL}"
else
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --display-name="Webtoon Collector Service Account" \
        --description="카카오 웹툰 수집 파이프라인용 서비스 계정"
    echo "✅ 서비스 계정 생성 완료: ${SERVICE_ACCOUNT_EMAIL}"
fi
echo ""

# 6. 서비스 계정 권한 부여
echo "6. 서비스 계정 권한 부여 중..."

# Cloud Functions 실행 권한
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.invoker" \
    --condition=None >/dev/null 2>&1 || echo "⚠️  run.invoker 권한 부여 실패 (이미 있을 수 있음)"

# GCS 읽기/쓰기 권한
gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT_EMAIL}:roles/storage.objectAdmin" "gs://${BUCKET_NAME}" || echo "⚠️  GCS 권한 부여 실패"

# BigQuery 읽기/쓰기 권한
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/bigquery.dataEditor" \
    --condition=None >/dev/null 2>&1 || echo "⚠️  BigQuery dataEditor 권한 부여 실패 (이미 있을 수 있음)"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/bigquery.jobUser" \
    --condition=None >/dev/null 2>&1 || echo "⚠️  BigQuery jobUser 권한 부여 실패 (이미 있을 수 있음)"

echo "✅ 권한 부여 완료"
echo ""

echo "=== GCP 인프라 준비 완료 ==="
echo ""
echo "다음 단계:"
echo "1. Cloud Functions 배포:"
echo "   cd functions/pipeline_function"
echo "   ./deploy.sh"
echo ""
echo "2. Cloud Scheduler 설정:"
echo "   scripts/setup/setup_scheduler.sh"

