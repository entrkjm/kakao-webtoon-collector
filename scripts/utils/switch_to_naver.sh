#!/bin/bash
# 네이버 웹툰 수집기 GCP 프로젝트로 전환

set -e

PROJECT_ID="naver-webtoon-collector"

echo "=== 네이버 웹툰 수집기 프로젝트로 전환 ==="
echo "프로젝트 ID: $PROJECT_ID"
echo ""

# 프로젝트 존재 확인
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
    echo "❌ 프로젝트가 존재하지 않습니다: $PROJECT_ID"
    exit 1
fi

# 프로젝트 설정
gcloud config set project "$PROJECT_ID"

# 현재 프로젝트 확인
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
    echo "✅ 프로젝트 전환 완료: $PROJECT_ID"
else
    echo "❌ 프로젝트 전환 실패"
    exit 1
fi

