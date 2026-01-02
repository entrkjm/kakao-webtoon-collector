# 모니터링 대시보드 생성 가이드

> **목표**: 파이프라인 상태를 한눈에 확인할 수 있는 대시보드 생성

---

## 📋 대시보드 항목

### 1. Cloud Function 실행 메트릭

#### 1.1 함수 실행 횟수
- **Metric**: `run.googleapis.com/request_count`
- **리소스**: Cloud Run Revision (`pipeline-function`)
- **집계**: Sum
- **기간**: Last 7 days

#### 1.2 함수 실행 시간
- **Metric**: `run.googleapis.com/request_latencies`
- **리소스**: Cloud Run Revision (`pipeline-function`)
- **집계**: Mean
- **기간**: Last 7 days

#### 1.3 에러 발생 횟수
- **Metric**: `run.googleapis.com/request_count`
- **리소스**: Cloud Run Revision (`pipeline-function`)
- **필터**: `response_code >= 400`
- **집계**: Sum
- **기간**: Last 7 days

### 2. Cloud Scheduler 실행 메트릭

#### 2.1 Scheduler Job 실행 횟수
- **Metric**: `cloudscheduler.googleapis.com/job/execution_count`
- **리소스**: Cloud Scheduler Job (`kakao-webtoon-weekly-collection`)
- **집계**: Sum
- **기간**: Last 7 days

#### 2.2 Scheduler Job 실패 횟수
- **Metric**: Log-based Metric (`scheduler-job-failure-count`)
- **리소스**: Cloud Scheduler Job (`kakao-webtoon-weekly-collection`)
- **집계**: Sum
- **기간**: Last 7 days

### 3. 데이터 수집 메트릭

#### 3.1 BigQuery 데이터 수집량
- **Metric**: BigQuery 테이블 레코드 수
- **쿼리**: `SELECT COUNT(*) FROM \`kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart\``
- **기간**: Last 7 days

---

## 🚀 생성 방법

> **참고**: CLI 스크립트는 JSON 형식 오류로 인해 Cloud Console에서 수동 생성하는 것을 권장합니다.

### 방법 1: Cloud Console에서 수동 생성 (권장) ⭐

#### 1단계: 대시보드 생성

1. [Cloud Monitoring > Dashboards](https://console.cloud.google.com/monitoring/dashboards?project=kakao-webtoon-collector) 접속
2. **"CREATE DASHBOARD"** 버튼 클릭
3. 대시보드 이름 입력: `Kakao Webtoon Pipeline Dashboard`

#### 2단계: 위젯 추가

**위젯 1: 함수 실행 횟수**

1. **"ADD CHART"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Run Revision"** 선택
4. Metric: **"Request count"** 선택
5. Filter: `service_name = pipeline-function`
6. **"Apply"** 클릭

**위젯 2: 함수 실행 시간**

1. **"ADD CHART"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Run Revision"** 선택
4. Metric: **"Request latencies"** 선택
5. Filter: `service_name = pipeline-function`
6. **"Apply"** 클릭

**위젯 3: 에러 발생 횟수**

1. **"ADD CHART"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Run Revision"** 선택
4. Metric: **"Request count"** 선택
5. Filter: `service_name = pipeline-function AND response_code >= 400`
6. **"Apply"** 클릭

**위젯 4: Scheduler Job 실행 상태**

1. **"ADD CHART"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Scheduler Job"** 선택
4. Metric: **"Execution count"** 선택
5. Filter: `job_id = kakao-webtoon-weekly-collection`
6. **"Apply"** 클릭

#### 3단계: 저장

1. **"SAVE"** 버튼 클릭
2. 대시보드 이름 확인
3. **"SAVE"** 클릭

---

### 방법 2: gcloud CLI로 생성 (고급)

네이버 프로젝트의 대시보드 JSON을 참고하여 생성:

```bash
# 네이버 프로젝트 참고
cat naver/scripts/monitoring/dashboard.json

# 카카오 프로젝트용으로 수정 후 생성
gcloud monitoring dashboards create \
    --config-from-file=dashboard.json \
    --project=kakao-webtoon-collector
```

---

## 📊 대시보드 구성 예시

```
┌─────────────────────────────────────────────────┐
│  Kakao Webtoon Pipeline Dashboard              │
├─────────────────────────────────────────────────┤
│  [함수 실행 횟수]    [함수 실행 시간]           │
│  [에러 발생 횟수]    [Scheduler 실행 상태]      │
│  [데이터 수집량]      [Alert 상태]              │
└─────────────────────────────────────────────────┘
```

---

## ✅ 완료 확인

대시보드 생성 후:

1. [Dashboards 페이지](https://console.cloud.google.com/monitoring/dashboards?project=kakao-webtoon-collector)에서 확인
2. 위젯이 정상적으로 데이터를 표시하는지 확인
3. 시간 범위를 조정하여 다양한 기간의 데이터 확인

---

## 📚 참고

- [네이버 프로젝트 모니터링 가이드](../naver/docs/monitoring/monitoring_guide.md)
- [Cloud Monitoring 문서](https://cloud.google.com/monitoring/dashboards)

---

**마지막 업데이트**: 2026-01-01

