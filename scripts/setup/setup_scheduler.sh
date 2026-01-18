#!/bin/bash
# Cloud Scheduler 설정 스크립트

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
JOB_NAME="kakao-webtoon-weekly-collection"
SCHEDULE="0 0 * * 1"  # 매주 월요일 오전 9시 KST (모든 요일 수집)
TIMEZONE="Asia/Seoul"  # 타임존 설정으로 자동 변환됨

# Cloud Functions URL 가져오기
FUNCTION_URL=$(gcloud functions describe "${FUNCTION_NAME}" --gen2 --region="${REGION}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")

if [ -z "$FUNCTION_URL" ]; then
    echo "❌ Cloud Functions를 찾을 수 없습니다."
    echo "먼저 Cloud Functions를 배포하세요:"
    echo "  cd functions/pipeline_function"
    echo "  ./deploy.sh"
    exit 1
fi

echo "=== Cloud Scheduler 설정 ==="
echo "프로젝트: $PROJECT_ID"
echo "함수명: $FUNCTION_NAME"
echo "함수 URL: $FUNCTION_URL"
echo "스케줄: $SCHEDULE ($TIMEZONE)"
echo ""

# 기존 작업이 있는지 확인
if gcloud scheduler jobs describe "${JOB_NAME}" --location="${REGION}" >/dev/null 2>&1; then
    echo "⚠️  작업이 이미 존재합니다. 업데이트합니다..."
    gcloud scheduler jobs update http "${JOB_NAME}" \
        --location="${REGION}" \
        --schedule="${SCHEDULE}" \
        --time-zone="${TIMEZONE}" \
        --uri="${FUNCTION_URL}" \
        --http-method=POST \
        --message-body='{"sort_keys": ["popularity", "views", "createdAt", "popularityMale", "popularityFemale"], "collect_all_weekdays": true}' \
        --description="카카오 웹툰 주간 차트 수집 (매주 월요일 오전 9시, 모든 요일 수집)" \
        --attempt-deadline=1800s
    echo "✅ 작업 업데이트 완료"
else
    echo "새 작업 생성 중..."
    gcloud scheduler jobs create http "${JOB_NAME}" \
        --location="${REGION}" \
        --schedule="${SCHEDULE}" \
        --time-zone="${TIMEZONE}" \
        --uri="${FUNCTION_URL}" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body='{"sort_keys": ["popularity", "views", "createdAt", "popularityMale", "popularityFemale"], "collect_all_weekdays": true}' \
        --description="카카오 웹툰 주간 차트 수집 (매주 월요일 오전 9시, 모든 요일 수집)" \
        --attempt-deadline=1800s
    echo "✅ 작업 생성 완료"
fi

echo ""
echo "=== Cloud Scheduler 설정 완료 ==="
echo ""
echo "작업 정보:"
gcloud scheduler jobs describe "${JOB_NAME}" --location="${REGION}" --format="yaml"

