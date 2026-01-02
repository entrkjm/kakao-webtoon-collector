# 카카오 웹툰 수집 파이프라인 - Cloud Functions

이 디렉토리는 Cloud Functions로 배포되는 파이프라인 코드를 포함합니다.

## 구조

```
pipeline_function/
├── main.py              # Cloud Functions 진입점
├── requirements.txt     # 의존성 패키지
├── deploy.sh           # 배포 스크립트
├── .gcloudignore       # 배포 제외 파일
└── src/                # 소스 코드 (배포 시 복사됨)
```

## 배포 방법

### 1. 사전 준비

```bash
# 프로젝트 설정
gcloud config set project kakao-webtoon-collector

# 필요한 API 활성화
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
```

### 2. 배포

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
  --set-env-vars "GCS_BUCKET_NAME=kakao-webtoon-raw,BIGQUERY_PROJECT_ID=kakao-webtoon-collector,BIGQUERY_DATASET_ID=kakao_webtoon" \
  --service-account="webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com"
```

## 로컬 테스트

Functions Framework를 사용하여 로컬에서 테스트할 수 있습니다:

```bash
# Functions Framework 설치
pip install functions-framework

# 로컬 실행
cd functions/pipeline_function
functions-framework --target=main --port=8080

# 다른 터미널에서 테스트
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-01-01", "sort_keys": ["popularity", "views"]}'
```

## 환경 변수

- `GCS_BUCKET_NAME`: GCS 버킷명 (기본값: `kakao-webtoon-raw`)
- `BIGQUERY_PROJECT_ID`: BigQuery 프로젝트 ID (기본값: `kakao-webtoon-collector`)
- `BIGQUERY_DATASET_ID`: BigQuery 데이터셋 ID (기본값: `kakao_webtoon`)

## 요청 형식

```json
{
  "date": "2026-01-01",  // 선택사항, 없으면 오늘 날짜
  "sort_keys": ["popularity", "views", "createdAt", "popularityMale", "popularityFemale"],  // 선택사항, 기본값: ["popularity"]
  "collect_all_weekdays": false,  // 선택사항, 모든 요일 수집 여부
  "limit": null  // 선택사항, 테스트용 제한
}
```

## 응답 형식

성공 시:
```json
{
  "status": "success",
  "date": "2026-01-01"
}
```

실패 시:
```json
{
  "error": "Error message"
}
```

