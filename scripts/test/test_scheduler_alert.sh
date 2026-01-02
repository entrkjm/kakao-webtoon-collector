#!/bin/bash
# Cloud Scheduler Alert Policy 테스트 스크립트

set -e

PROJECT_ID="kakao-webtoon-collector"
JOB_NAME="kakao-webtoon-weekly-collection"
REGION="asia-northeast3"

echo "=== Cloud Scheduler Alert Policy 테스트 ==="
echo ""

# 1. 현재 설정 백업
echo "1. 현재 Scheduler Job 설정 확인 중..."
CURRENT_URI=$(gcloud scheduler jobs describe "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(httpTarget.uri)' 2>/dev/null)

CURRENT_SERVICE_ACCOUNT=$(gcloud scheduler jobs describe "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(httpTarget.oidcToken.serviceAccountEmail)' 2>/dev/null)

CURRENT_METHOD=$(gcloud scheduler jobs describe "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(httpTarget.httpMethod)' 2>/dev/null)

CURRENT_BODY=$(gcloud scheduler jobs describe "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(httpTarget.body)' 2>/dev/null)

# Headers 가져오기 (세미콜론으로 구분된 형식)
CURRENT_HEADERS=$(gcloud scheduler jobs describe "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(httpTarget.headers)' 2>/dev/null || echo "")

echo "✅ 현재 URI: $CURRENT_URI"
echo "✅ 현재 Service Account: $CURRENT_SERVICE_ACCOUNT"
echo ""

# 2. 잘못된 URL로 변경
echo "2. 잘못된 URL로 변경 중..."
# Headers는 업데이트 시 자동으로 유지되므로 URI만 변경
gcloud scheduler jobs update http "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --uri="https://invalid-url-for-test-$(date +%s).com" \
    --oidc-service-account-email="$CURRENT_SERVICE_ACCOUNT" \
    --http-method="$CURRENT_METHOD" \
    --message-body="$CURRENT_BODY" \
    2>&1 | grep -v "Waiting on" || true

echo "✅ 잘못된 URL로 변경 완료"
echo ""

# 3. Job 실행 (실패 예상)
echo "3. Scheduler Job 실행 중 (실패 예상)..."
gcloud scheduler jobs run "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    2>&1 | grep -v "Waiting on" || echo "⚠️  Job 실행 완료 (실패 예상)"
echo ""

# 4. 잠시 대기 (실패 로그 기록 대기)
echo "⏱️  10초 대기 중 (실패 로그 기록 대기)..."
sleep 10

# 5. 원래 URL로 복구
echo "4. 원래 URL로 복구 중..."
# Headers는 업데이트 시 자동으로 유지되므로 URI만 변경
gcloud scheduler jobs update http "$JOB_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --uri="$CURRENT_URI" \
    --oidc-service-account-email="$CURRENT_SERVICE_ACCOUNT" \
    --http-method="$CURRENT_METHOD" \
    --message-body="$CURRENT_BODY" \
    2>&1 | grep -v "Waiting on" || true

echo "✅ 원래 URL로 복구 완료"
echo ""

# 6. 안내
echo "=== 테스트 완료 ==="
echo ""
echo "⏱️  1-2분 후 확인:"
echo ""
echo "1. Incidents 페이지:"
echo "   https://console.cloud.google.com/monitoring/alerting/incidents?project=$PROJECT_ID"
echo ""
echo "2. 이메일 알림 확인:"
echo "   - entrkjm@vaiv.kr"
echo "   - entrkjm@gmail.com"
echo ""
echo "3. Scheduler Job 실행 기록 확인:"
echo "   gcloud scheduler jobs describe $JOB_NAME --location=$REGION --project=$PROJECT_ID --format='value(status.lastAttemptTime,status.lastAttemptStatus)'"
echo ""
echo "✅ Cloud Scheduler Alert Policy 테스트 완료!"

