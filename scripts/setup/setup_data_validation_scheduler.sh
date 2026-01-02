#!/bin/bash
# 데이터 검증 Cloud Scheduler 설정 스크립트

set -e

PROJECT_ID="${GCP_PROJECT_ID:-kakao-webtoon-collector}"
REGION="${GCP_REGION:-asia-northeast3}"
FUNCTION_NAME="data-validation-function"
SCHEDULER_NAME="data-validation-scheduler"
SCHEDULE="${SCHEDULE:-0 10 * * 1}"  # 매주 월요일 오전 10시 (수집 후 1시간)

echo "=== 데이터 검증 Cloud Scheduler 설정 ==="
echo "프로젝트: $PROJECT_ID"
echo "스케줄러 이름: $SCHEDULER_NAME"
echo "스케줄: $SCHEDULE (매주 월요일 오전 10시)"
echo ""

# Cloud Function URL 가져오기
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
    --gen2 \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(serviceConfig.uri)" \
    2>&1 | grep -v "Waiting on")

if [ -z "$FUNCTION_URL" ]; then
    echo "❌ Cloud Function을 찾을 수 없습니다. 먼저 배포하세요:"
    echo "   cd functions/data_validation_function && ./deploy.sh"
    exit 1
fi

echo "Cloud Function URL: $FUNCTION_URL"
echo ""

# 기존 스케줄러 삭제 (있는 경우)
echo "기존 스케줄러 확인 중..."
if gcloud scheduler jobs describe "$SCHEDULER_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    >/dev/null 2>&1; then
    echo "기존 스케줄러 삭제 중..."
    gcloud scheduler jobs delete "$SCHEDULER_NAME" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --quiet \
        2>&1 | grep -v "Waiting on"
fi

# Cloud Scheduler 작업 생성
echo "Cloud Scheduler 작업 생성 중..."
gcloud scheduler jobs create http "$SCHEDULER_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --schedule="$SCHEDULE" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --message-body='{"date": null}' \
    --headers="Content-Type=application/json" \
    --time-zone="Asia/Seoul" \
    --description="매주 파이프라인 데이터 수집 상태 검증 (매주 월요일 오전 10시)" \
    --attempt-deadline=1800s \
    2>&1 | grep -v "Waiting on"

echo ""
echo "✅ Cloud Scheduler 설정 완료!"
echo ""
echo "스케줄러 확인:"
gcloud scheduler jobs describe "$SCHEDULER_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format="table(name,schedule,timeZone,state)" \
    2>&1 | grep -v "Waiting on"

echo ""
echo "다음 실행 시간:"
gcloud scheduler jobs describe "$SCHEDULER_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(scheduleTime)" \
    2>&1 | grep -v "Waiting on"

echo ""
echo "수동 실행 테스트:"
echo "  gcloud scheduler jobs run $SCHEDULER_NAME --location=$REGION --project=$PROJECT_ID"

