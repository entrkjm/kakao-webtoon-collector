# 카카오 웹툰 수집기 배포 체크리스트

이 문서는 카카오 웹툰 수집기를 GCP에 배포하기 위한 단계별 체크리스트입니다.

## ✅ 사전 준비

- [ ] gcloud CLI 설치 및 인증 완료
  ```bash
  gcloud auth login
  gcloud auth application-default login
  ```

- [ ] 결제 계정 연결 (Always Free 사용을 위해 필요)

---

## 1단계: GCP 프로젝트 생성

### 1.1 프로젝트 생성

```bash
# 프로젝트 생성
gcloud projects create kakao-webtoon-collector \
  --name="카카오 웹툰 수집기"

# 프로젝트 ID 확인
gcloud projects list | grep kakao-webtoon-collector
```

**확인 사항**:
- [ ] 프로젝트 생성 완료
- [ ] 프로젝트 ID: `kakao-webtoon-collector`

### 1.2 프로젝트로 전환

```bash
# 프로젝트 전환 스크립트 사용
cd scripts/utils
./switch_to_kakao.sh

# 또는 수동으로
gcloud config set project kakao-webtoon-collector
```

**확인 사항**:
- [ ] 현재 프로젝트가 `kakao-webtoon-collector`인지 확인
  ```bash
  gcloud config get-value project
  ```

---

## 2단계: GCP 인프라 설정

### 2.1 인프라 자동 설정

```bash
cd scripts/setup
./setup_gcp_prerequisites.sh
```

이 스크립트는 다음을 수행합니다:
- [ ] 필요한 API 활성화
  - Cloud Functions API
  - Cloud Run API
  - Cloud Storage API
  - BigQuery API
  - Cloud Scheduler API
- [ ] GCS 버킷 생성 (`kakao-webtoon-raw`)
- [ ] BigQuery 데이터셋 생성 (`kakao_webtoon`)
- [ ] BigQuery 테이블 생성 (`dim_webtoon`, `fact_weekly_chart`)
- [ ] 서비스 계정 생성 (`webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com`)
- [ ] 서비스 계정 권한 부여

**확인 사항**:
- [ ] 모든 API 활성화 완료
- [ ] GCS 버킷 생성 확인
  ```bash
  gsutil ls -b gs://kakao-webtoon-raw
  ```
- [ ] BigQuery 데이터셋 생성 확인
  ```bash
  bq ls -d kakao-webtoon-collector:kakao_webtoon
  ```
- [ ] BigQuery 테이블 생성 확인
  ```bash
  bq ls kakao-webtoon-collector:kakao_webtoon
  ```
- [ ] 서비스 계정 생성 확인
  ```bash
  gcloud iam service-accounts describe webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com
  ```

---

## 3단계: Cloud Functions 배포

### 3.1 배포 준비

```bash
cd functions/pipeline_function

# src 디렉토리 확인
ls -la ../../src
```

**확인 사항**:
- [ ] `src/` 디렉토리가 존재하는지 확인
- [ ] `main.py`, `requirements.txt` 파일 확인

### 3.2 Cloud Functions 배포

```bash
./deploy.sh
```

**확인 사항**:
- [ ] 배포 성공 메시지 확인
- [ ] 함수 URL 확인
  ```bash
  gcloud functions describe pipeline_function \
    --gen2 \
    --region=asia-northeast3 \
    --format="value(serviceConfig.uri)"
  ```

### 3.3 배포 검증

```bash
# 함수 상태 확인
gcloud functions describe pipeline_function \
  --gen2 \
  --region=asia-northeast3 \
  --format="yaml(state,updateTime)"
```

**확인 사항**:
- [ ] 함수 상태가 `ACTIVE`인지 확인
- [ ] 최근 업데이트 시간 확인

---

## 4단계: Cloud Scheduler 설정

### 4.1 Scheduler 작업 생성

```bash
cd ../../scripts/setup
./setup_scheduler.sh
```

**확인 사항**:
- [ ] 작업 생성/업데이트 완료
- [ ] 스케줄 확인: 매주 월요일 오전 9시 (Asia/Seoul)
- [ ] 작업 상태 확인
  ```bash
  gcloud scheduler jobs describe kakao-webtoon-weekly-collection \
    --location=asia-northeast3 \
    --format="yaml(state,schedule,timeZone)"
  ```

---

## 5단계: 테스트

### 5.1 수동 실행 테스트

```bash
# 함수 URL 가져오기
FUNCTION_URL=$(gcloud functions describe pipeline_function \
  --gen2 \
  --region=asia-northeast3 \
  --format="value(serviceConfig.uri)")

# 테스트 요청
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-01-01",
    "sort_keys": ["popularity"],
    "collect_all_weekdays": false
  }'
```

**확인 사항**:
- [ ] HTTP 200 응답 확인
- [ ] 응답 본문에 `"status": "success"` 확인

### 5.2 GCS 데이터 확인

```bash
# 업로드된 파일 확인
gsutil ls -r gs://kakao-webtoon-raw/raw_data/
```

**확인 사항**:
- [ ] JSON 파일이 업로드되었는지 확인
- [ ] 날짜별 디렉터리 구조 확인

### 5.3 BigQuery 데이터 확인

```sql
-- 데이터 확인
SELECT 
  chart_date,
  COUNT(DISTINCT webtoon_id) AS webtoon_count,
  COUNT(*) AS total_records
FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
GROUP BY chart_date
ORDER BY chart_date DESC
LIMIT 10;

-- 상위 10개 웹툰 확인
SELECT 
  w.title,
  c.rank,
  c.sort_key
FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart` c
JOIN `kakao-webtoon-collector.kakao_webtoon.dim_webtoon` w
  ON c.webtoon_id = w.webtoon_id
WHERE c.chart_date = '2026-01-01'
  AND c.sort_key = 'popularity'
ORDER BY c.rank
LIMIT 10;
```

**확인 사항**:
- [ ] 데이터가 정상적으로 저장되었는지 확인
- [ ] 레코드 수 확인
- [ ] 정렬 옵션별 데이터 확인

### 5.4 Cloud Scheduler 수동 실행 테스트

```bash
# Scheduler 작업 수동 실행
gcloud scheduler jobs run kakao-webtoon-weekly-collection \
  --location=asia-northeast3
```

**확인 사항**:
- [ ] 작업 실행 성공
- [ ] Cloud Functions 로그 확인
  ```bash
  gcloud functions logs read pipeline_function \
    --gen2 \
    --region=asia-northeast3 \
    --limit=50
  ```

---

## 6단계: 모니터링 설정 (선택사항)

### 6.1 알림 설정

필요시 네이버 프로젝트와 동일하게 알림 정책을 설정할 수 있습니다.

**참고**: 네이버 프로젝트의 알림 설정 참고
- `naver/docs/setup/alert_setup_complete_guide.md`

### 6.2 비용 모니터링

```bash
# 비용 확인
gcloud billing projects describe kakao-webtoon-collector \
  --format="value(billingAccountName)"
```

**확인 사항**:
- [ ] 결제 계정 연결 확인
- [ ] Always Free 범위 내 사용 확인

---

## 문제 해결

### 문제 1: 프로젝트 생성 실패

**원인**: 프로젝트 ID가 이미 사용 중이거나 권한 부족

**해결**:
```bash
# 다른 프로젝트 ID 사용
gcloud projects create kakao-webtoon-collector-2 \
  --name="카카오 웹툰 수집기"
```

### 문제 2: API 활성화 실패

**원인**: 권한 부족 또는 결제 계정 미연결

**해결**:
```bash
# 프로젝트에 결제 계정 연결 확인
gcloud billing projects describe kakao-webtoon-collector
```

### 문제 3: Cloud Functions 배포 실패

**원인**: 서비스 계정 권한 부족

**해결**:
```bash
# 서비스 계정 권한 확인
gcloud projects get-iam-policy kakao-webtoon-collector \
  --flatten="bindings[].members" \
  --filter="bindings.members:webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com"
```

### 문제 4: BigQuery 업로드 실패

**원인**: 테이블 스키마 불일치 또는 권한 부족

**해결**:
```bash
# 테이블 스키마 확인
bq show kakao-webtoon-collector:kakao_webtoon.dim_webtoon
bq show kakao-webtoon-collector:kakao_webtoon.fact_weekly_chart
```

---

## 완료 확인

모든 단계를 완료했는지 확인:

- [ ] GCP 프로젝트 생성 완료
- [ ] 인프라 설정 완료 (GCS, BigQuery, 서비스 계정)
- [ ] Cloud Functions 배포 완료
- [ ] Cloud Scheduler 설정 완료
- [ ] 수동 실행 테스트 성공
- [ ] 데이터 확인 완료 (GCS, BigQuery)

---

**마지막 업데이트**: 2026-01-01

