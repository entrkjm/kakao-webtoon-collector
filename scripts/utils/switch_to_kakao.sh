#!/bin/bash
# 카카오 웹툰 수집기 GCP 프로젝트로 전환

set -e

PROJECT_ID="kakao-webtoon-collector"

echo "=== 카카오 웹툰 수집기 프로젝트로 전환 ==="
echo "프로젝트 ID: $PROJECT_ID"
echo ""

# 프로젝트 존재 확인
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
    echo "⚠️  프로젝트가 존재하지 않습니다: $PROJECT_ID"
    echo ""
    echo "프로젝트를 생성하시겠습니까? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "프로젝트 생성 중..."
        gcloud projects create "$PROJECT_ID" --name="카카오 웹툰 수집기"
        echo "✅ 프로젝트 생성 완료"
    else
        echo "프로젝트를 먼저 생성하세요:"
        echo "  gcloud projects create $PROJECT_ID --name=\"카카오 웹툰 수집기\""
        exit 1
    fi
fi

# 프로젝트 설정
gcloud config set project "$PROJECT_ID"

# 현재 프로젝트 확인
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
    echo "✅ 프로젝트 전환 완료: $PROJECT_ID"
    echo ""
    echo "다음 단계:"
    echo "1. 인프라 설정: cd scripts/setup && ./setup_gcp_prerequisites.sh"
    echo "2. Cloud Functions 배포: cd functions/pipeline_function && ./deploy.sh"
else
    echo "❌ 프로젝트 전환 실패"
    exit 1
fi

