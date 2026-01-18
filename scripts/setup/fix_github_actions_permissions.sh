#!/bin/bash
# GitHub Actions 배포 권한 수정 스크립트

set -e

PROJECT_ID="kakao-webtoon-collector"
SERVICE_ACCOUNT_EMAIL="webtoon-collector@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== GitHub Actions 배포 권한 수정 ==="
echo "프로젝트: $PROJECT_ID"
echo "서비스 계정: $SERVICE_ACCOUNT_EMAIL"
echo ""

# 현재 프로젝트 확인
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "⚠️  현재 프로젝트가 다릅니다: $CURRENT_PROJECT"
    echo "프로젝트를 변경합니다..."
    gcloud config set project "$PROJECT_ID"
fi

echo "1. 서비스 계정이 자신을 사용할 수 있도록 권한 부여..."
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT_EMAIL" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/iam.serviceAccountUser" \
    --project="$PROJECT_ID" \
    --quiet

echo ""
echo "2. Compute Engine 기본 서비스 계정 정보 확인..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo "   프로젝트 번호: $PROJECT_NUMBER"
echo "   Compute Engine 서비스 계정: $COMPUTE_SA"
echo "   Cloud Build 서비스 계정: $CLOUD_BUILD_SA"
echo ""

echo "3. webtoon-collector가 Compute Engine 서비스 계정을 사용할 수 있도록 권한 부여..."
gcloud iam service-accounts add-iam-policy-binding "$COMPUTE_SA" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/iam.serviceAccountUser" \
    --project="$PROJECT_ID" \
    --quiet

echo ""
echo "4. webtoon-collector에 Cloud Build Builder 역할 부여..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/cloudbuild.builds.builder" \
    --quiet

echo ""
echo "4-1. webtoon-collector에 Cloud Run Admin 역할 부여 (Gen2 함수 업데이트용)..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.admin" \
    --quiet

echo ""
echo "5. Compute Engine 서비스 계정에 필요한 역할 부여..."
# Cloud Functions Developer 역할
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/cloudfunctions.developer" \
    --quiet

# Cloud Build Builder 역할 (경고 해결)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/cloudbuild.builds.builder" \
    --quiet

echo ""
echo "6. Cloud Build 서비스 계정에 권한 부여..."
# Cloud Build 서비스 계정에 serviceAccountUser 역할 부여
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT_EMAIL" \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --project="$PROJECT_ID" \
    --quiet

# Cloud Build 서비스 계정에 Cloud Functions Developer 역할 부여
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/cloudfunctions.developer" \
    --quiet

echo ""
echo "✅ 권한 설정 완료!"
echo ""
echo "설정된 권한:"
echo "  1. $SERVICE_ACCOUNT_EMAIL → 자신에게 serviceAccountUser 역할"
echo "  2. $SERVICE_ACCOUNT_EMAIL → $COMPUTE_SA에 serviceAccountUser 역할"
echo "  3. $SERVICE_ACCOUNT_EMAIL → 프로젝트에 cloudbuild.builds.builder 역할"
echo "  4. $SERVICE_ACCOUNT_EMAIL → 프로젝트에 run.admin 역할 (Gen2 함수 업데이트용)"
echo "  5. $COMPUTE_SA → 프로젝트에 cloudfunctions.developer 역할"
echo "  6. $COMPUTE_SA → 프로젝트에 cloudbuild.builds.builder 역할"
echo "  7. $CLOUD_BUILD_SA → $SERVICE_ACCOUNT_EMAIL에 serviceAccountUser 역할"
echo "  8. $CLOUD_BUILD_SA → 프로젝트에 cloudfunctions.developer 역할"

