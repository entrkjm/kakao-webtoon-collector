# 결제 계정 연결 가이드

카카오 웹툰 수집기 프로젝트에 결제 계정을 연결하는 방법입니다.

## 중요 사항

**Always Free 티어를 사용하려면 결제 계정이 필요합니다.**

- Always Free 티어는 무료이지만, 결제 계정 연결이 필수입니다
- 실제로 비용이 발생하지 않도록 Always Free 범위 내에서만 사용합니다
- 결제 계정이 없으면 일부 API를 활성화할 수 없습니다

## 결제 계정 연결 방법

### 방법 1: gcloud CLI 사용

```bash
# 결제 계정 목록 확인
gcloud billing accounts list

# 프로젝트에 결제 계정 연결
gcloud billing projects link kakao-webtoon-collector \
  --billing-account=BILLING_ACCOUNT_ID
```

`BILLING_ACCOUNT_ID`는 `gcloud billing accounts list` 명령어로 확인할 수 있습니다.

### 방법 2: GCP 콘솔 사용

1. [GCP 콘솔](https://console.cloud.google.com/) 접속
2. 프로젝트 선택: `kakao-webtoon-collector`
3. 메뉴 → 결제 → 결제 계정 연결
4. 결제 계정 선택 및 연결

## 결제 계정 연결 확인

```bash
# 프로젝트의 결제 계정 확인
gcloud billing projects describe kakao-webtoon-collector \
  --format="value(billingAccountName)"
```

## 결제 계정 연결 후

결제 계정을 연결한 후 다음 명령어를 다시 실행하세요:

```bash
cd scripts/setup
./setup_gcp_prerequisites.sh
```

## 비용 관리

### Always Free 범위

- **GCS**: 5GB 저장, 5,000 Class A 작업/월
- **BigQuery**: 10GB 저장, 1TB 쿼리/월
- **Cloud Functions**: 200만 요청/월, 400,000GB-초/월
- **Cloud Scheduler**: 3개 작업 무료

### 예산 알림 설정 (선택사항)

비용이 발생하지 않도록 예산을 설정할 수 있습니다:

```bash
# 예산 생성 (예: $1)
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="카카오 웹툰 수집기 예산" \
  --budget-amount=1USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

**참고**: 네이버 웹툰 수집기 프로젝트(`naver-webtoon-collector`)에 이미 결제 계정이 연결되어 있다면, 같은 결제 계정을 카카오 프로젝트에도 연결할 수 있습니다.

