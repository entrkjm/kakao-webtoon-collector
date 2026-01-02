# GCP 인프라 설정 가이드

카카오 웹툰 수집 파이프라인을 GCP에서 실행하기 위한 인프라 설정 가이드입니다.

## 사전 준비

1. **GCP 프로젝트 생성**
   ```bash
   # 카카오 웹툰 수집기 프로젝트 생성
   gcloud projects create kakao-webtoon-collector \
     --name="카카오 웹툰 수집기"
   
   # 프로젝트로 전환 (스크립트 사용)
   cd scripts/utils
   ./switch_to_kakao.sh
   
   # 또는 수동으로
   gcloud config set project kakao-webtoon-collector
   ```
   
   **참고**: 네이버 웹툰 수집기는 `naver-webtoon-collector` 프로젝트를 사용합니다.
   카카오는 독립 프로젝트(`kakao-webtoon-collector`)를 사용하여 Always Free 티어를 각각 활용합니다.

2. **gcloud CLI 인증**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

## 1. GCP 인프라 사전 준비

### 방법 1: 빠른 배포 (권장)

모든 단계를 한 번에 실행:

```bash
# 프로젝트 생성 및 전환
gcloud projects create kakao-webtoon-collector --name="카카오 웹툰 수집기"
cd scripts/utils
./switch_to_kakao.sh

# 빠른 배포 실행
cd ../../scripts/setup
./quick_deploy.sh
```

### 방법 2: 단계별 배포

각 단계를 개별적으로 실행:

```bash
cd scripts/setup
./setup_gcp_prerequisites.sh
```

이 스크립트는 다음을 수행합니다:
- 필요한 API 활성화
- GCS 버킷 생성 (`kakao-webtoon-raw`)
- BigQuery 데이터셋 생성 (`kakao_webtoon`)
- BigQuery 테이블 생성 (`dim_webtoon`, `fact_weekly_chart`)
- 서비스 계정 생성 및 권한 부여

### 수동 설정 (선택사항)

#### GCS 버킷 생성
```bash
gsutil mb -l asia-northeast3 gs://kakao-webtoon-raw
```

#### BigQuery 데이터셋 생성
```bash
bq mk --dataset --location=asia-northeast3 PROJECT_ID:kakao_webtoon
```

#### BigQuery 테이블 생성
```bash
bq query --use_legacy_sql=false < scripts/setup/setup_bigquery.sql
```

또는 BigQuery 콘솔에서 `scripts/setup/setup_bigquery.sql` 파일의 내용을 직접 실행

## 2. Cloud Functions 배포

```bash
cd functions/pipeline_function
./deploy.sh
```

또는 수동 배포:

```bash
gcloud functions deploy pipeline_function \
  --gen2 \
  --runtime=python39 \
  --region=asia-northeast3 \
  --source=. \
  --entry-point=main \
  --trigger-http \
  --allow-unauthenticated \
  --timeout=3600s \
  --memory=512MB \
  --set-env-vars "GCS_BUCKET_NAME=kakao-webtoon-raw,BIGQUERY_PROJECT_ID=YOUR_PROJECT_ID,BIGQUERY_DATASET_ID=kakao_webtoon" \
  --service-account="webtoon-collector@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```

## 3. Cloud Scheduler 설정

```bash
cd scripts/setup
./setup_scheduler.sh
```

이 스크립트는 매주 월요일 오전 9시에 자동으로 파이프라인을 실행하는 스케줄을 생성합니다.

### 수동 설정 (선택사항)

```bash
# Cloud Functions URL 가져오기
FUNCTION_URL=$(gcloud functions describe pipeline_function --gen2 --region=asia-northeast3 --format="value(serviceConfig.uri)")

# Scheduler 작업 생성
gcloud scheduler jobs create http kakao-webtoon-weekly-collection \
  --location=asia-northeast3 \
  --schedule="0 9 * * 1" \
  --time-zone="Asia/Seoul" \
  --uri="$FUNCTION_URL" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"sort_keys": ["popularity", "views", "createdAt", "popularityMale", "popularityFemale"], "collect_all_weekdays": false}'
```

## 4. 테스트

### 수동 실행 테스트

```bash
# Cloud Functions URL 가져오기
FUNCTION_URL=$(gcloud functions describe pipeline_function --gen2 --region=asia-northeast3 --format="value(serviceConfig.uri)")

# 테스트 요청
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-01-01",
    "sort_keys": ["popularity"],
    "collect_all_weekdays": false
  }'
```

### GCS 확인

```bash
# 업로드된 파일 확인
gsutil ls -r gs://kakao-webtoon-raw/raw_html/
```

### BigQuery 확인

```sql
-- 데이터 확인
SELECT COUNT(*) as total_records
FROM `YOUR_PROJECT_ID.kakao_webtoon.fact_weekly_chart`
WHERE chart_date = '2026-01-01';

-- 상위 10개 웹툰 확인
SELECT 
  w.title,
  c.rank,
  c.sort_key
FROM `YOUR_PROJECT_ID.kakao_webtoon.fact_weekly_chart` c
JOIN `YOUR_PROJECT_ID.kakao_webtoon.dim_webtoon` w
  ON c.webtoon_id = w.webtoon_id
WHERE c.chart_date = '2026-01-01'
  AND c.sort_key = 'popularity'
ORDER BY c.rank
LIMIT 10;
```

## 환경 변수

Cloud Functions 배포 시 설정되는 환경 변수:

- `GCS_BUCKET_NAME`: GCS 버킷명 (기본값: `kakao-webtoon-raw`)
- `BIGQUERY_PROJECT_ID`: BigQuery 프로젝트 ID (기본값: `kakao-webtoon-collector`)
- `BIGQUERY_DATASET_ID`: BigQuery 데이터셋 ID (기본값: `kakao_webtoon`)
- `DATA_FORMAT`: 데이터 저장 형식 (기본값: `jsonl`)

## 프로젝트 전환

네이버와 카카오 프로젝트 간 전환:

```bash
# 카카오 프로젝트로 전환
cd scripts/utils
./switch_to_kakao.sh

# 네이버 프로젝트로 전환
./switch_to_naver.sh
```

## 비용 고려사항

GCP Always Free 범위 내에서 운영하도록 설계되었습니다:

- **GCS**: 5GB 저장, 5,000 Class A 작업/월
- **BigQuery**: 10GB 저장, 1TB 쿼리/월
- **Cloud Functions**: 200만 요청/월, 400,000GB-초/월
- **Cloud Scheduler**: 3개 작업 무료

주 1회 실행 기준으로 충분히 무료 범위 내입니다.

## 문제 해결

### Cloud Functions 배포 실패
- 서비스 계정 권한 확인
- API 활성화 확인 (`cloudfunctions.googleapis.com`, `run.googleapis.com`)

### BigQuery 업로드 실패
- 서비스 계정에 `bigquery.dataEditor`, `bigquery.jobUser` 권한 확인
- 테이블 스키마 확인

### GCS 업로드 실패
- 서비스 계정에 `storage.objectAdmin` 권한 확인
- 버킷 존재 여부 확인

