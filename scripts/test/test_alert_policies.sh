#!/bin/bash
# Alert Policy 테스트 스크립트

set -e

PROJECT_ID="kakao-webtoon-collector"
FUNCTION_NAME="pipeline-function"
REGION="asia-northeast3"

echo "=== Alert Policy 테스트 ==="
echo "프로젝트: $PROJECT_ID"
echo ""

# 1. Cloud Function URL 가져오기
echo "1. Cloud Function URL 확인 중..."
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
    --gen2 \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(serviceConfig.uri)" 2>/dev/null)

if [ -z "$FUNCTION_URL" ]; then
    echo "❌ Cloud Function을 찾을 수 없습니다."
    exit 1
fi

echo "✅ Cloud Function URL: $FUNCTION_URL"
echo ""

# 2. 테스트 선택
echo "=== 테스트 선택 ==="
echo "1. Cloud Function ERROR 테스트 (pipeline-function-error-count)"
echo "2. Cloud Scheduler 실패 테스트 (scheduler-job-failure-count)"
echo "3. 둘 다 테스트"
echo ""
read -p "선택 (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "=== Cloud Function ERROR 테스트 ==="
        echo "잘못된 요청으로 ERROR 발생 중..."
        curl -X POST "$FUNCTION_URL" \
            -H "Content-Type: application/json" \
            -d '{"date":"invalid-date"}' \
            -s -o /dev/null
        echo "✅ ERROR 로그 발생 완료"
        echo ""
        echo "⏱️  1-2분 후 확인:"
        echo "   - Incidents: https://console.cloud.google.com/monitoring/alerting/incidents?project=$PROJECT_ID"
        echo "   - 이메일: entrkjm@vaiv.kr, entrkjm@gmail.com"
        ;;
    2)
        echo ""
        echo "=== Cloud Scheduler 실패 테스트 ==="
        echo "Scheduler Job 수동 실행 중..."
        gcloud scheduler jobs run kakao-webtoon-weekly-collection \
            --location="$REGION" \
            --project="$PROJECT_ID" 2>&1 || echo "⚠️  Job 실행 중 오류 발생 (의도된 실패일 수 있음)"
        echo ""
        echo "⏱️  1-2분 후 확인:"
        echo "   - Incidents: https://console.cloud.google.com/monitoring/alerting/incidents?project=$PROJECT_ID"
        echo "   - 이메일: entrkjm@vaiv.kr, entrkjm@gmail.com"
        ;;
    3)
        echo ""
        echo "=== Cloud Function ERROR 테스트 ==="
        echo "잘못된 요청으로 ERROR 발생 중..."
        curl -X POST "$FUNCTION_URL" \
            -H "Content-Type: application/json" \
            -d '{"date":"invalid-date"}' \
            -s -o /dev/null
        echo "✅ ERROR 로그 발생 완료"
        echo ""
        echo "=== Cloud Scheduler 실패 테스트 ==="
        echo "Scheduler Job 수동 실행 중..."
        gcloud scheduler jobs run kakao-webtoon-weekly-collection \
            --location="$REGION" \
            --project="$PROJECT_ID" 2>&1 || echo "⚠️  Job 실행 중 오류 발생 (의도된 실패일 수 있음)"
        echo ""
        echo "⏱️  1-2분 후 확인:"
        echo "   - Incidents: https://console.cloud.google.com/monitoring/alerting/incidents?project=$PROJECT_ID"
        echo "   - 이메일: entrkjm@vaiv.kr, entrkjm@gmail.com"
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac

echo ""
echo "=== 테스트 완료 ==="
echo ""
echo "확인 사항:"
echo "1. Incidents 페이지에서 Alert 확인"
echo "2. 이메일 알림 확인 (스팸 폴더 포함)"
echo "3. 각 Metric이 정상 작동하는지 확인"

