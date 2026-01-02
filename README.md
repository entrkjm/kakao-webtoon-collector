# 카카오 웹툰 주간 차트 수집 파이프라인

네이버 웹툰 수집기와 동일한 구조로 구현된 카카오 웹툰 주간 차트 데이터 수집 파이프라인입니다.

## 📋 프로젝트 개요

- **목적**: 카카오 웹툰 주간 차트 데이터를 주기적으로 수집하여 BigQuery에 저장
- **아키텍처**: ELT (Extract-Load-Transform) 파이프라인
- **실행 주기**: 주 1회 (매주 월요일 오전 9시)
- **GCP 프로젝트**: `kakao-webtoon-collector` (독립 프로젝트)

## 🏗️ 아키텍처

### ELT 구조
1. **Extract**: 카카오 웹툰 API에서 데이터 수집
2. **Load Raw**: GCS에 JSON 원본 저장
3. **Transform**: 데이터 파싱 및 정규화
4. **Load Refined**: BigQuery에 정제된 데이터 저장

### 인프라 구성
- **로컬 개발**: 파일 시스템으로 GCS/BigQuery 대체
- **GCP 배포**: Cloud Functions + Cloud Scheduler + GCS + BigQuery
- **비용**: GCP Always Free 범위 내 설계

## 📊 데이터 모델

### dim_webtoon (마스터 테이블)
- `webtoon_id` (PRIMARY KEY)
- `title`, `author`, `genre`, `tags`
- `created_at`, `updated_at`

### fact_weekly_chart (히스토리 테이블)
- `chart_date` (PARTITION KEY)
- `webtoon_id` (FOREIGN KEY)
- `rank`, `sort_key`
- `weekday`, `year`, `month`, `week`
- `view_count`, `collected_at`

## 🚀 시작하기

### 1. 로컬 개발 환경 설정

```bash
# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 로컬 실행

```bash
# 기본 실행 (단일 정렬 옵션)
python src/run_pipeline.py --date 2026-01-01 --sort-keys popularity

# 모든 정렬 옵션 수집
python src/run_pipeline.py --date 2026-01-01 --all-sorts

# 모든 요일 + 모든 정렬
python src/run_pipeline.py --date 2026-01-01 --all-weekdays --all-sorts
```

### 3. GCP 배포

#### 3.1 GCP 프로젝트 생성 및 설정

```bash
# 프로젝트 생성
gcloud projects create kakao-webtoon-collector \
  --name="카카오 웹툰 수집기"

# 프로젝트로 전환
cd scripts/utils
./switch_to_kakao.sh
```

#### 3.2 인프라 설정

```bash
cd scripts/setup
./setup_gcp_prerequisites.sh
```

이 스크립트는 다음을 수행합니다:
- 필요한 API 활성화
- GCS 버킷 생성 (`kakao-webtoon-raw`)
- BigQuery 데이터셋 및 테이블 생성
- 서비스 계정 생성 및 권한 부여

#### 3.3 Cloud Functions 배포

```bash
cd functions/pipeline_function
./deploy.sh
```

#### 3.4 Cloud Scheduler 설정

```bash
cd scripts/setup
./setup_scheduler.sh
```

## 📁 프로젝트 구조

```
kakao/
├── src/                    # 핵심 로직
│   ├── extract.py         # API 데이터 수집
│   ├── parse_api.py       # API 응답 파싱
│   ├── transform.py       # 데이터 변환
│   ├── upload_gcs.py      # GCS 업로드
│   ├── upload_bigquery.py  # BigQuery 업로드
│   ├── models.py          # 데이터 모델
│   └── utils.py           # 유틸리티
├── functions/             # Cloud Functions
│   └── pipeline_function/
│       ├── main.py        # HTTP 트리거 진입점
│       ├── deploy.sh      # 배포 스크립트
│       └── test_local.py  # 로컬 테스트
├── scripts/               # 배포/설정 스크립트
│   ├── setup/            # 인프라 설정
│   └── utils/            # 유틸리티 (프로젝트 전환 등)
└── docs/                 # 문서
    └── setup/            # 설정 가이드
```

## 🔧 설정

### 환경 변수

로컬 실행 시:
```bash
export GCS_BUCKET_NAME=kakao-webtoon-raw
export BIGQUERY_PROJECT_ID=kakao-webtoon-collector
export BIGQUERY_DATASET_ID=kakao_webtoon
```

GCS/BigQuery 업로드 활성화:
```bash
export UPLOAD_TO_GCS=true
export UPLOAD_TO_BIGQUERY=true
```

### 프로젝트 전환

네이버와 카카오 프로젝트 간 전환:

```bash
# 카카오 프로젝트로 전환
cd scripts/utils
./switch_to_kakao.sh

# 네이버 프로젝트로 전환
./switch_to_naver.sh
```

## 📊 정렬 옵션

카카오 웹툰은 클라이언트 사이드 정렬을 지원합니다:
- `popularity`: 전체 인기순
- `views`: 조회순
- `createdAt`: 최신순
- `popularityMale`: 남성 인기순
- `popularityFemale`: 여성 인기순

## 🔍 데이터 확인

### BigQuery 쿼리 예시

```sql
-- 최근 수집된 데이터 확인
SELECT 
  chart_date,
  COUNT(DISTINCT webtoon_id) AS webtoon_count,
  COUNT(*) AS total_records
FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
GROUP BY chart_date
ORDER BY chart_date DESC
LIMIT 10;

-- 특정 날짜의 상위 10개 웹툰
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

## 📚 문서

- [GCP 설정 가이드](docs/setup/GCP_SETUP_GUIDE.md)
- [프로젝트 구조 결정 문서](docs/setup/PROJECT_STRUCTURE_DECISION.md)
- [완료 상태](COMPLETION_STATUS.md)
- [다음 단계](NEXT_STEPS.md)

## 💡 네이버 웹툰 수집기와의 차이점

1. **독립 GCP 프로젝트**: `kakao-webtoon-collector` (네이버는 `naver-webtoon-collector`)
2. **정렬 방식**: 클라이언트 사이드 정렬 지원
3. **API 구조**: 카카오 웹툰 API 구조에 맞춤

## 🔗 관련 프로젝트

- [네이버 웹툰 수집기](../naver/README.md)

---

**마지막 업데이트**: 2026-01-01
