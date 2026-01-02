# 모니터링 대시보드 생성 - 단계별 가이드

> **목표**: Cloud Console에서 모니터링 대시보드를 수동으로 생성

---

## 📋 사전 준비

1. GCP 프로젝트: `kakao-webtoon-collector`
2. 필요한 리소스:
   - Cloud Function: `pipeline-function` (Cloud Run Revision)
   - Cloud Scheduler: `kakao-webtoon-weekly-collection`

---

## 🚀 단계별 생성 방법

### 1단계: 대시보드 페이지 접속

1. [Cloud Monitoring > Dashboards](https://console.cloud.google.com/monitoring/dashboards?project=kakao-webtoon-collector) 접속
2. **"CREATE DASHBOARD"** 버튼 클릭

### 2단계: 대시보드 이름 설정

1. 대시보드 이름 입력: **"Kakao Webtoon Pipeline Dashboard"**
2. 화면 하단 또는 중앙의 **"Add widget"** 버튼 클릭하여 첫 번째 위젯 추가 시작

---

### 3단계: 위젯 1 - Pipeline Function 실행 횟수

1. **"Add widget"** 모달에서 **"Data"** 섹션의 **"Metric"** 클릭
   - (막대 그래프 아이콘이 있는 항목)

2. **"Configure widget"** 화면에서:
   - **"Select a metric"** 드롭다운 클릭 (화면 중앙 "A Metric" 옆)
   
3. **리소스 타입 선택**:
   - 검색창에 **"Cloud Run Revision"** 입력
   - 또는 리소스 목록에서 **"Cloud Run Revision"** 선택

4. **Metric 선택**:
   - **"Request count"** 검색 또는 선택
   - 또는 **"run.googleapis.com/request_count"** 선택

5. **필터 추가**:
   - **"Filter Add filter"** 클릭
   - 필드: **"service_name"** 선택
   - 값: **"pipeline-function"** 입력

6. **위젯 타입 설정**:
   - 오른쪽 **"Display"** 패널에서
   - **"Widget type"** 드롭다운: **"Line chart"** 선택 (기본값일 수 있음)

7. **위젯 제목 설정**:
   - **"Widget title"** 입력란에 **"Pipeline Function 실행 횟수"** 입력

8. **"Apply"** 버튼 클릭 (오른쪽 상단)

---

### 4단계: 위젯 2 - Pipeline Function 실행 시간

1. **"Add widget"** 버튼 클릭
2. **"Data"** 섹션의 **"Metric"** 클릭
3. **"Select a metric"** 드롭다운 클릭
4. **리소스 타입**: **"Cloud Run Revision"** 선택
5. **Metric**: **"Request latencies"** 선택
6. **필터 추가**:
   - **"Filter Add filter"** 클릭
   - 필드: **"service_name"** 선택
   - 값: **"pipeline-function"** 입력
7. **위젯 타입**: **"Line chart"** 선택 (Display 패널)
8. **위젯 제목**: **"Pipeline Function 실행 시간"** 입력
9. **"Apply"** 버튼 클릭

---

### 5단계: 위젯 3 - Pipeline Function 에러 발생 횟수

1. **"Add widget"** 버튼 클릭
2. **"Data"** 섹션의 **"Metric"** 클릭
3. **"Select a metric"** 드롭다운 클릭
4. **리소스 타입**: **"Cloud Run Revision"** 선택
5. **Metric**: **"Request count"** 선택
6. **필터 추가**:
   - **"Filter Add filter"** 클릭
   - 필드: **"service_name"** 선택
   - 값: **"pipeline-function"** 입력
   - **"Filter Add filter"** 클릭 (추가)
   - 필드: **"response_code"** 선택
   - **연산자 및 값 설정**:
     - **방법 1 (권장)**: 연산자 **"!="** 선택 후 값 **"200"** 입력
       - 200이 아닌 모든 응답(에러)을 포함합니다
     - **방법 2**: 연산자가 "="만 있다면, 여러 필터를 추가:
       - response_code = "400"
       - response_code = "401"
       - response_code = "403"
       - response_code = "404"
       - response_code = "500"
       - (각각 별도 필터로 추가하면 OR 조건으로 자동 처리됨)
     - **방법 3**: response_code_class 필드가 있다면:
       - 필드: "response_code_class" 선택
       - 값: "4xx" 또는 "5xx" 입력
7. **위젯 타입**: **"Line chart"** 선택 (Display 패널)
8. **위젯 제목**: **"Pipeline Function 에러 발생 횟수"** 입력
9. **"Apply"** 버튼 클릭

---

### 6단계: 위젯 4 - Cloud Scheduler 작업 실행 횟수

1. **"Add widget"** 버튼 클릭
2. **"Data"** 섹션의 **"Metric"** 클릭
3. **"Select a metric"** 드롭다운 클릭
4. **메트릭 선택**:
   - **방법 1 (권장)**: **"Log entries"** 메트릭 선택
     - `logging.googleapis.com/log_entry_count`
     - Scheduler Job의 모든 실행 로그를 카운트하여 실행 횟수와 유사한 결과 제공
   - **방법 2**: **"scheduler-job-failure-count"** 메트릭 선택
     - 실패 횟수만 보여줍니다 (실행 횟수는 아님)
   - **방법 3**: 이 위젯 스킵
     - 3개 위젯만으로도 충분합니다
6. **필터 추가** (Log entries 메트릭 사용 시):
   - **방법 1**: **"Filter Add filter"** 입력 필드에 직접 입력:
     - `resource.type="cloud_scheduler_job"` 입력 후 Enter
     - `resource.labels.job_id="kakao-webtoon-weekly-collection"` 입력 후 Enter
   - **방법 2**: **"by"** 드롭다운 사용:
     - **"by"** 드롭다운 클릭
     - **"Resource labels"** 섹션에서 **"job_id"** 선택
     - 값: **"kakao-webtoon-weekly-collection"** 입력
   - **방법 3**: 필터 없이 진행 (선택사항)
     - 필터 없이도 진행 가능하며, 나중에 필요하면 추가 가능
   
   **또는** (scheduler-job-failure-count 메트릭 사용 시):
   - 필터는 자동으로 적용되거나 별도 추가 불필요
7. **위젯 타입**: **"Line chart"** 또는 **"Scorecard"** 선택
   - Line chart: 시간에 따른 추이 확인
   - Scorecard: 현재 총 실행 횟수 확인
8. **위젯 제목**: **"Cloud Scheduler 작업 실행 횟수"** 입력
9. **"Apply"** 버튼 클릭

---

### 7단계: 대시보드 저장

1. 모든 위젯 추가 완료 후 **"SAVE"** 버튼 클릭
2. 대시보드 이름 확인: **"Kakao Webtoon Pipeline Dashboard"**
3. **"SAVE"** 클릭

---

## ✅ 완료 확인

대시보드 생성 후:

1. [Dashboards 페이지](https://console.cloud.google.com/monitoring/dashboards?project=kakao-webtoon-collector)에서 **"Kakao Webtoon Pipeline Dashboard"** 확인
2. 4개의 위젯이 정상적으로 표시되는지 확인
3. 시간 범위를 조정하여 다양한 기간의 데이터 확인

---

## 📊 대시보드 구성

```
┌─────────────────────────────────────────────────┐
│  Kakao Webtoon Pipeline Dashboard              │
├─────────────────────────────────────────────────┤
│  [Pipeline Function 실행 횟수]                 │
│  [Pipeline Function 실행 시간]                 │
│  [Pipeline Function 에러 발생 횟수]            │
│  [Cloud Scheduler 작업 실행 횟수]              │
└─────────────────────────────────────────────────┘
```

---

## 🔍 문제 해결

### 위젯에 데이터가 표시되지 않는 경우

1. **시간 범위 확인**: 기본값이 "Last 1 hour"일 수 있으므로 "Last 7 days"로 변경
2. **필터 확인**: `service_name`과 `job_id` 값이 정확한지 확인
3. **리소스 타입 확인**: Cloud Run Revision과 Cloud Scheduler Job이 올바른지 확인

### 메트릭을 찾을 수 없는 경우

1. **Cloud Run Revision 메트릭**: `run.googleapis.com/request_count`, `run.googleapis.com/request_latencies`
2. **Cloud Scheduler 메트릭**: `cloudscheduler.googleapis.com/job/execution_count`
3. 메트릭 이름을 직접 검색하여 확인

---

## 📚 참고

- [Cloud Monitoring 문서](https://cloud.google.com/monitoring/dashboards)
- [메트릭 목록](https://cloud.google.com/monitoring/api/metrics)

---

**마지막 업데이트**: 2026-01-01

