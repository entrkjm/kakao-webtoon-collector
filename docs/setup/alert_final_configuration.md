# Alert Policy 최종 설정 요약

> **작성일**: 2026-01-01  
> **상태**: 모든 Alert Policy 정상 작동 확인 ✅

---

## 📋 설정된 Alert Policy 목록

### 1. Pipeline Function Execution Failure

**목적**: Cloud Function 실행 중 ERROR 발생 시 알림

**설정**:
- **리소스 타입**: Cloud Run Revision
- **Metric**: Log-based Metric (`pipeline-function-error-count`)
- **필터**:
  - `resource.type = "cloud_run_revision"`
  - `resource.labels.service_name = "pipeline-function"`
  - `metric.labels.severity = "ERROR"` (Metric labels)
- **Threshold**: `0` (0보다 크면 Alert)
- **Duration**: `1 minute` (60초)
- **알림 채널**: 
  - entrkjm@vaiv.kr
  - entrkjm@gmail.com

**Log-based Metric**:
- **이름**: `pipeline-function-error-count`
- **필터**: `textPayload=~"ERROR"`
- **설명**: Pipeline Function의 ERROR 로그를 카운트

**테스트 결과**: ✅ 정상 작동 (약 2-3분 후 메일 도착)

---

### 2. Pipeline Scheduler Job Failure

**목적**: Cloud Scheduler Job 실패 시 알림

**설정**:
- **리소스 타입**: Cloud Scheduler Job
- **Metric**: Log-based Metric (`scheduler-job-failure-count`)
- **필터**:
  - `resource.type = "cloud_scheduler_job"`
  - `resource.labels.job_id = "kakao-webtoon-weekly-collection"`
  - `metric.type = "logging.googleapis.com/user/scheduler-job-failure-count"`
- **Threshold**: `0 /s` (초당 0개보다 크면 Alert = 실패 1개라도 발생하면)
- **Duration**: `1 minute` (60초)
- **알림 채널**: 
  - entrkjm@vaiv.kr
  - entrkjm@gmail.com

**Log-based Metric**:
- **이름**: `scheduler-job-failure-count`
- **필터**: 
  ```
  resource.type="cloud_scheduler_job" 
  AND resource.labels.job_id="kakao-webtoon-weekly-collection" 
  AND (
    textPayload=~"ERROR" OR 
    textPayload=~"FAILED" OR 
    textPayload=~"failed" OR 
    jsonPayload.status="UNKNOWN" OR 
    jsonPayload.status="FAILED" OR 
    jsonPayload.debugInfo=~"ERROR"
  )
  ```
- **설명**: Scheduler Job 실패 로그를 카운트 (textPayload + jsonPayload 모두 확인)

**테스트 결과**: ✅ 정상 작동 (약 3-5분 후 메일 도착, 필터 수정 직후)

---

## 📊 Alert 지연 시간

### Pipeline Function Alert
- **예상 시간**: 2-3분
- **구성**:
  - Duration: 1 minute
  - Metric 수집: 30초 ~ 1분
  - 이메일 전송: 10초 ~ 1분

### Pipeline Scheduler Alert
- **예상 시간**: 2-3분 (일반), 3-5분 (필터 수정 직후)
- **구성**:
  - Duration: 1 minute
  - Metric 수집: 30초 ~ 1분 (필터 수정 직후는 더 오래 걸릴 수 있음)
  - 이메일 전송: 10초 ~ 1분

---

## 🔧 주요 설정 포인트

### Threshold Value: 0 /s
- **의미**: "초당 0개보다 크면" Alert 트리거
- **실제 의미**: 실패가 1개라도 발생하면 Alert
- **이유**: Job 실패는 즉시 알림이 필요하므로

### Duration: 1 minute
- **의미**: 1분 동안 조건을 만족해야 Alert 트리거
- **이유**: 너무 짧으면 노이즈가 많고, 너무 길면 Alert가 늦게 트리거됨

### Log-based Metric 필터
- **Pipeline Function**: `textPayload=~"ERROR"` (간단)
- **Scheduler Job**: `textPayload + jsonPayload` 모두 확인 (복잡하지만 정확)

---

## ✅ 확인 사항

### Alert Policy 상태
```bash
gcloud alpha monitoring policies list \
    --project=kakao-webtoon-collector \
    --format="table(displayName,enabled)"
```

**예상 결과**:
- Pipeline Function Execution Failure: True
- Pipeline Scheduler Job Failure: True

### 알림 채널
```bash
gcloud alpha monitoring channels list \
    --project=kakao-webtoon-collector \
    --format="table(displayName,labels.email_address)"
```

**예상 결과**:
- Pipeline Alert Email 1: entrkjm@vaiv.kr
- Pipeline Alert Email 2: entrkjm@gmail.com

---

## 📝 참고

### Alert 확인 방법
1. **Incidents 페이지**:
   ```
   https://console.cloud.google.com/monitoring/alerting/incidents?project=kakao-webtoon-collector
   ```

2. **이메일**:
   - entrkjm@vaiv.kr
   - entrkjm@gmail.com

### 테스트 방법
- **Pipeline Function**: `./kakao/scripts/test/test_alert_policies.sh` (옵션 1)
- **Pipeline Scheduler**: `./kakao/scripts/test/test_scheduler_alert.sh`

---

**마지막 업데이트**: 2026-01-01

