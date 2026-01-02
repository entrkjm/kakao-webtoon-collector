#!/bin/bash
# 빠른 배포 스크립트 - 모든 단계를 한 번에 실행

set -e

echo "=========================================="
echo "카카오 웹툰 수집기 빠른 배포"
echo "=========================================="
echo ""

# 프로젝트 ID 확인
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ 프로젝트가 설정되지 않았습니다."
    echo ""
    echo "먼저 프로젝트를 생성하고 전환하세요:"
    echo "  1. gcloud projects create kakao-webtoon-collector --name=\"카카오 웹툰 수집기\""
    echo "  2. cd scripts/utils && ./switch_to_kakao.sh"
    exit 1
fi

if [ "$PROJECT_ID" != "kakao-webtoon-collector" ]; then
    echo "⚠️  현재 프로젝트가 kakao-webtoon-collector가 아닙니다: $PROJECT_ID"
    echo ""
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "프로젝트를 전환하세요: cd scripts/utils && ./switch_to_kakao.sh"
        exit 1
    fi
fi

echo "현재 프로젝트: $PROJECT_ID"
echo ""

# 스크립트 디렉터리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 1단계: 인프라 설정
echo "=========================================="
echo "1단계: GCP 인프라 설정"
echo "=========================================="
cd "$SCRIPT_DIR"
./setup_gcp_prerequisites.sh

if [ $? -ne 0 ]; then
    echo "❌ 인프라 설정 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "2단계: Cloud Functions 배포"
echo "=========================================="
cd "$PROJECT_ROOT/functions/pipeline_function"
./deploy.sh

if [ $? -ne 0 ]; then
    echo "❌ Cloud Functions 배포 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "3단계: Cloud Scheduler 설정"
echo "=========================================="
cd "$SCRIPT_DIR"
./setup_scheduler.sh

if [ $? -ne 0 ]; then
    echo "❌ Cloud Scheduler 설정 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 배포 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. 수동 실행 테스트:"
echo "   FUNCTION_URL=\$(gcloud functions describe pipeline_function --gen2 --region=asia-northeast3 --format=\"value(serviceConfig.uri)\")"
echo "   curl -X POST \"\$FUNCTION_URL\" -H \"Content-Type: application/json\" -d '{\"date\": \"2026-01-01\", \"sort_keys\": [\"popularity\"]}'"
echo ""
echo "2. 데이터 확인:"
echo "   - GCS: gsutil ls -r gs://kakao-webtoon-raw/raw_data/"
echo "   - BigQuery: BigQuery 콘솔에서 쿼리 실행"
echo ""
echo "3. Scheduler 수동 실행 테스트:"
echo "   gcloud scheduler jobs run kakao-webtoon-weekly-collection --location=asia-northeast3"

