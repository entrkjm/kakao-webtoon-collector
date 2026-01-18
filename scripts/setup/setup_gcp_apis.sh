#!/bin/bash
# GCP 필요한 API 활성화 스크립트

set -e

# 프로젝트 ID 확인
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ 프로젝트가 설정되지 않았습니다."
    echo "먼저 다음 명령어를 실행하세요:"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "=== GCP API 활성화 ==="
echo "프로젝트: $PROJECT_ID"
echo ""

# 필요한 API 목록
APIS=(
    "cloudfunctions.googleapis.com"
    "cloudscheduler.googleapis.com"
    "bigquery.googleapis.com"
    "storage.googleapis.com"
    "cloudbuild.googleapis.com"
    "run.googleapis.com"
    "cloudresourcemanager.googleapis.com"
)

echo "다음 API를 활성화합니다:"
for API in "${APIS[@]}"; do
    echo "  - $API"
done
echo ""

# API 활성화
for API in "${APIS[@]}"; do
    echo "활성화 중: $API"
    gcloud services enable "$API" --project="$PROJECT_ID" || echo "  (이미 활성화됨 또는 오류)"
done

echo ""
echo "✅ 모든 API 활성화 완료!"
echo ""
echo "활성화된 API 확인:"
gcloud services list --enabled --project="$PROJECT_ID" | grep -E "$(IFS='|'; echo "${APIS[*]}")"

