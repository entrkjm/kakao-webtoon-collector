#!/bin/bash
# Cloud Monitoring Alert Policy 설정 스크립트
# 파이프라인 실패 감지 및 알림 설정

set -e

PROJECT_ID="${GCP_PROJECT_ID:-kakao-webtoon-collector}"
REGION="${GCP_REGION:-asia-northeast3}"
NOTIFICATION_CHANNEL_EMAILS="${NOTIFICATION_CHANNEL_EMAILS:-entrkjm@gmail.com}"

echo "=== Cloud Monitoring Alert Policy 설정 ==="
echo "프로젝트: $PROJECT_ID"
echo ""

# 프로젝트 확인
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "⚠️  현재 프로젝트가 $CURRENT_PROJECT입니다."
    echo "프로젝트를 $PROJECT_ID로 전환합니다..."
    gcloud config set project "$PROJECT_ID"
fi

# 알림 채널 이메일 주소 설정 (쉼표로 구분된 여러 이메일 지원)
if [ -z "$NOTIFICATION_CHANNEL_EMAILS" ]; then
    echo "⚠️  NOTIFICATION_CHANNEL_EMAILS 환경 변수가 설정되지 않았습니다."
    echo "이메일 주소를 입력하세요 (여러 개일 경우 쉼표로 구분):"
    read -r NOTIFICATION_CHANNEL_EMAILS
fi

# 이메일 주소를 배열로 변환
IFS=',' read -ra EMAIL_ARRAY <<< "$NOTIFICATION_CHANNEL_EMAILS"

echo "알림 이메일: ${#EMAIL_ARRAY[@]}개"
for email in "${EMAIL_ARRAY[@]}"; do
    echo "  - $(echo $email | xargs)"  # 공백 제거
done
echo ""

# 알림 채널 생성 (여러 개)
echo "1. 알림 채널 생성 중..."
CHANNEL_IDS=()

for i in "${!EMAIL_ARRAY[@]}"; do
    email=$(echo "${EMAIL_ARRAY[$i]}" | xargs)  # 공백 제거
    CHANNEL_DISPLAY_NAME="Pipeline Alert Email $((i+1))"
    
    echo "  채널 $((i+1)) 생성 중: $email"
    
    # 기존 채널 확인 (이메일 주소로 검색)
    EXISTING_CHANNEL=$(gcloud alpha monitoring channels list \
        --filter="labels.email_address=$email" \
        --format="value(name)" \
        --limit=1 \
        --project="$PROJECT_ID" \
        2>&1 | grep -v "Waiting on" | grep -v "WARNING" | head -1 || echo "")
    
    if [ -n "$EXISTING_CHANNEL" ] && [[ "$EXISTING_CHANNEL" == projects/* ]]; then
        echo "  ✅ 기존 채널 발견: $EXISTING_CHANNEL"
        CHANNEL_IDS+=("$EXISTING_CHANNEL")
    else
        # 새 채널 생성
        echo "  새 채널 생성 중..."
        NEW_CHANNEL_ID=$(gcloud alpha monitoring channels create \
            --display-name="$CHANNEL_DISPLAY_NAME" \
            --type=email \
            --channel-labels=email_address="$email" \
            --format="value(name)" \
            --project="$PROJECT_ID" \
            2>&1 | grep -v "Waiting on" | grep -v "WARNING" | head -1 || echo "")
        
        if [ -n "$NEW_CHANNEL_ID" ] && [[ "$NEW_CHANNEL_ID" == projects/* ]]; then
            echo "  ✅ 채널 생성 완료: $NEW_CHANNEL_ID"
            CHANNEL_IDS+=("$NEW_CHANNEL_ID")
        else
            echo "  ⚠️  채널 생성 실패: $email"
            echo "     수동으로 생성하세요:"
            echo "     gcloud alpha monitoring channels create --display-name=\"$CHANNEL_DISPLAY_NAME\" --type=email --channel-labels=email_address=\"$email\" --project=$PROJECT_ID"
        fi
    fi
done

if [ ${#CHANNEL_IDS[@]} -eq 0 ]; then
    echo "❌ 알림 채널을 생성할 수 없습니다."
    exit 1
fi

echo ""
echo "✅ 총 ${#CHANNEL_IDS[@]}개 알림 채널 생성/확인 완료"
echo ""

# 채널 ID를 쉼표로 구분된 문자열로 변환 (Alert Policy에 사용)
CHANNEL_IDS_STRING=$(IFS=','; echo "${CHANNEL_IDS[*]}")
echo "알림 채널 IDs: $CHANNEL_IDS_STRING"
echo ""

# Alert Policy 1: Cloud Function 실행 실패
echo "2. Cloud Function 실행 실패 Alert Policy 생성 중..."
cat > /tmp/alert_policy_function_failure.json <<EOF
{
  "displayName": "Pipeline Function Execution Failure",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Cloud Function execution failed",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"pipeline-function\" AND severity=\"ERROR\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0,
        "duration": "60s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE"
          }
        ]
      }
    }
  ],
  "notificationChannels": [$(printf '"%s",' "${CHANNEL_IDS[@]}" | sed 's/,$//')]
}
EOF

gcloud alpha monitoring policies create \
    --policy-from-file=/tmp/alert_policy_function_failure.json \
    --project="$PROJECT_ID" \
    2>&1 | grep -v "Waiting on" | grep -v "WARNING" || echo "⚠️  Alert Policy 생성 실패 (이미 존재할 수 있음)"

echo "✅ Cloud Function 실행 실패 Alert Policy 생성 완료"
echo ""

# Alert Policy 2: Cloud Scheduler 작업 실패
echo "3. Cloud Scheduler 작업 실패 Alert Policy 생성 중..."
cat > /tmp/alert_policy_scheduler_failure.json <<EOF
{
  "displayName": "Pipeline Scheduler Job Failure",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Cloud Scheduler job failed",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_scheduler_job\" AND resource.labels.job_id=\"kakao-webtoon-weekly-collection\" AND metric.type=\"scheduler.googleapis.com/job/failed_execution_count\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0,
        "duration": "60s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE"
          }
        ]
      }
    }
  ],
  "notificationChannels": [$(printf '"%s",' "${CHANNEL_IDS[@]}" | sed 's/,$//')]
}
EOF

gcloud alpha monitoring policies create \
    --policy-from-file=/tmp/alert_policy_scheduler_failure.json \
    --project="$PROJECT_ID" \
    2>&1 | grep -v "Waiting | grep -v "WARNING" || echo "⚠️  Alert Policy 생성 실패 (이미 존재할 수 있음)"

echo "✅ Cloud Scheduler 작업 실패 Alert Policy 생성 완료"
echo ""

# Alert Policy 3: 데이터 검증 함수 실패
echo "4. 데이터 검증 함수 실패 Alert Policy 생성 중..."
cat > /tmp/alert_policy_data_validation_failure.json <<EOF
{
  "displayName": "Data Validation Function Failure",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Data validation function failed",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"data-validation-function\" AND severity=\"ERROR\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0,
        "duration": "60s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE"
          }
        ]
      }
    }
  ],
  "notificationChannels": [$(printf '"%s",' "${CHANNEL_IDS[@]}" | sed 's/,$//')]
}
EOF

gcloud alpha monitoring policies create \
    --policy-from-file=/tmp/alert_policy_data_validation_failure.json \
    --project="$PROJECT_ID" \
    2>&1 | grep -v "Waiting on" | grep -v "WARNING" || echo "⚠️  Alert Policy 생성 실패 (이미 존재할 수 있음)"

echo "✅ 데이터 검증 함수 실패 Alert Policy 생성 완료"
echo ""

echo "✅ Alert Policy 설정 완료!"
echo ""
echo "생성된 Alert Policies:"
gcloud alpha monitoring policies list \
    --project="$PROJECT_ID" \
    --format="table(displayName,enabled)" \
    2>&1 | grep -E "(displayName|Pipeline|Data)" || echo "Alert Policy 목록 조회 실패"
echo ""
echo "알림 채널 확인:"
gcloud alpha monitoring channels list \
    --project="$PROJECT_ID" \
    --format="table(displayName,labels.email_address)" \
    2>&1 | grep -E "(displayName|Pipeline)" || echo "알림 채널 목록 조회 실패"

