# Alert Policy 설정 가이드 (카카오 웹툰 수집기)

> **목표**: 파이프라인 실패 시 이메일 알림 받기
> 
> **핵심**: 하나의 Alert Policy를 만들고, 여러 개의 Filter를 추가합니다. 나중에 같은 Policy에 Condition을 추가할 수 있습니다.

---

## 📋 목차

1. [사전 준비](#사전-준비)
2. [Alert Policy 1: Cloud Function 실행 실패](#alert-policy-1-cloud-function-실행-실패)
3. [Alert Policy 2: Cloud Scheduler 작업 실패](#alert-policy-2-cloud-scheduler-작업-실패)
4. [완료 확인](#완료-확인)
5. [테스트](#테스트)

---

## 사전 준비

### 알림 채널 확인

다음 명령어로 알림 채널이 생성되어 있는지 확인:

```bash
gcloud alpha monitoring channels list \
    --format="table(displayName,labels.email_address)" \
    --project=kakao-webtoon-collector
```

**예상 결과**:
- Pipeline Alert Email 1 (entrkjm@vaiv.kr)
- Pipeline Alert Email 2 (entrkjm@gmail.com)

**알림 채널이 없으면 생성**:

다음 두 개의 알림 채널을 생성해야 합니다:

1. [Cloud Monitoring > 알림](https://console.cloud.google.com/monitoring/alerting?project=kakao-webtoon-collector) 접속
2. "알림 채널" → "알림 채널 만들기"
3. 첫 번째 채널:
   - 이메일 주소: `entrkjm@vaiv.kr`
   - 표시 이름: `Pipeline Alert Email 1`
   - "만들기" 클릭
4. 두 번째 채널:
   - "알림 채널 만들기" 다시 클릭
   - 이메일 주소: `entrkjm@gmail.com`
   - 표시 이름: `Pipeline Alert Email 2`
   - "만들기" 클릭

✅ 알림 채널이 2개 있으면 준비 완료입니다.

---

## Alert Policy 1: Cloud Function 실행 실패

> **핵심**: 네이버 프로젝트와 동일하게 설정합니다.
> - Filter 1: `service_name = pipeline-function` (Resource labels)
> - Filter 2: `severity = ERROR` (Metric labels)
> 
> **참고**: 네이버 프로젝트에서도 동일한 설정으로 작동하고 있습니다.

### 1단계: Alert Policy 생성 시작

1. [Cloud Monitoring Alerting 페이지](https://console.cloud.google.com/monitoring/alerting?project=kakao-webtoon-collector) 접속
2. **"CREATE POLICY"** 버튼 클릭

### 2단계: Resource Type 및 Metric 선택

> **⚠️ 중요**: Cloud Function Gen2는 실제로 Cloud Run Revision 리소스 타입을 사용합니다. **"Cloud Function"을 선택하면 실패할 수 있으므로, 반드시 "Cloud Run Revision"을 직접 선택해야 합니다!**

1. **"Select a metric"** 클릭
2. 왼쪽 리소스 목록에서 **"Cloud Run Revision"** 클릭
   > **참고**: "Cloud Function"이 아닌 **"Cloud Run Revision"**을 직접 선택해야 합니다!
3. 나타나는 메트릭 목록에서 **"Log entry count"** 또는 **"Log entries"** 선택
4. **"Apply"** 버튼 클릭

### 3단계: Filter 추가 (여러 개 추가)

> **핵심**: 하나의 Condition에 여러 개의 Filter를 추가합니다.

화면 오른쪽에 **"Resource labels"** 섹션과 **"Metric labels"** 섹션이 나타나면:

#### Filter 1: service_name (Resource labels)

1. **"Resource labels"** 섹션에서 **"Add filter"** 또는 **"+"** 버튼 클릭
2. **"Filter"** 입력 필드에 `service_name` 입력 (또는 드롭다운에서 `resource.labels.service_name` 선택)
3. **"Comparator"**: `=` 선택
4. **"Value"**: `pipeline-function` 입력
5. **"Done"** 버튼 클릭

#### Filter 2: severity (Metric labels)

> **⚠️ 중요**: 네이버 프로젝트와 동일하게 `metric.labels.severity` 필터를 추가합니다.

1. **"Metric labels"** 섹션에서 **"Add filter"** 또는 **"+"** 버튼 클릭
   - 또는 화면 하단의 **"Add a filter"** 링크 클릭
2. **"Filter"** 입력 필드에 `severity` 입력
   - 또는 드롭다운에서 `metric.labels.severity` 선택 (있는 경우)
3. **"Comparator"**: `=` 선택
4. **"Value"**: `ERROR` 입력
   > **참고**: 드롭다운에 ERROR가 없어도 직접 입력하면 됩니다.
5. **"Done"** 버튼 클릭

**Filter preview 확인**:
화면에 다음과 같은 필터 미리보기가 표시되어야 합니다:
```
resource.type="cloud_run_revision"
resource.labels.service_name="pipeline-function"
metric.labels.severity="ERROR"
```

> **참고**: 네이버 프로젝트에서도 동일한 필터 조합을 사용하고 있으며 정상 작동합니다.

### 4단계: Alert Condition 설정

1. 왼쪽 메뉴에서 **"Configure trigger"** 클릭
2. **Condition type**: `Threshold` (이미 선택됨)
3. **Alert trigger**: `Any time series violates` (이미 선택됨)
4. **Threshold position**: `Above threshold` (이미 선택됨)
5. **Threshold value**: `0` 입력 ← 중요!
6. **Advanced Options** 클릭:
   - **Duration**: `1 minute` 선택 ← **반드시 설정 필요!** (0초로 설정되면 Alert가 트리거되지 않을 수 있음)

### 5단계: 알림 채널 추가

1. 왼쪽 메뉴에서 **"Notifications and name"** 클릭
2. **"Notification Channels"** 또는 **"Add notification channels"** 클릭
3. 다음 2개 채널 모두 선택:
   - ✅ Pipeline Alert Email 1 (entrkjm@vaiv.kr)
   - ✅ Pipeline Alert Email 2 (entrkjm@gmail.com)
4. **"OK"** 또는 **"Select"** 클릭

### 6단계: 이름 입력 및 저장

1. **"Alert policy name"** 입력란에:
   ```
   Pipeline Function Execution Failure
   ```
2. 하단의 **"Create Policy"** 버튼 클릭

✅ **첫 번째 Alert Policy 완료!**

> **참고**: 나중에 `data-validation-function`도 감지하려면, 이 Alert Policy를 편집하여 "+ Add alert condition" 버튼으로 두 번째 Condition을 추가하면 됩니다. 자세한 방법은 [네이버 프로젝트 Alert Policy 수정 가이드](../naver/docs/setup/alert_policy_edit_guide.md)를 참고하세요.

---

## Alert Policy 2: Cloud Scheduler 작업 실패

### 1단계: Alert Policy 생성 시작

1. 다시 **"CREATE POLICY"** 버튼 클릭

### 2단계: Resource Type 및 Metric 선택

1. **"Select a metric"** 클릭
2. 왼쪽 리소스 목록에서 **"Cloud Scheduler Job"** 클릭
3. 나타나는 메트릭 목록에서 **"Job failed execution count"** 선택
4. **"Apply"** 버튼 클릭

### 3단계: Filter 추가

화면 오른쪽에 **"Resource labels"** 섹션이 나타나면:

1. **"Resource labels"** 섹션에서 **"Add filter"** 또는 **"+"** 버튼 클릭
2. **"Filter"** 입력 필드에 `job_id` 입력
3. **"Comparator"**: `=` 선택
4. **"Value"**: `kakao-webtoon-weekly-collection` 입력
5. **"Done"** 버튼 클릭

### 4단계: Alert Condition 설정

1. 왼쪽 메뉴에서 **"Configure trigger"** 클릭
2. **Condition type**: `Threshold` (이미 선택됨)
3. **Alert trigger**: `Any time series violates` (이미 선택됨)
4. **Threshold position**: `Above threshold` (이미 선택됨)
5. **Threshold value**: `0` 입력
6. **Advanced Options** → **Duration**: `1 minute` 선택

### 5단계: 알림 채널 추가

1. 왼쪽 메뉴에서 **"Notifications and name"** 클릭
2. **"Notification Channels"** 클릭
3. 다음 2개 채널 모두 선택:
   - ✅ Pipeline Alert Email 1 (entrkjm@vaiv.kr)
   - ✅ Pipeline Alert Email 2 (entrkjm@gmail.com)
4. **"OK"** 클릭

### 6단계: 이름 입력 및 저장

1. **"Alert policy name"** 입력란에:
   ```
   Pipeline Scheduler Job Failure
   ```
2. 하단의 **"Create Policy"** 버튼 클릭

✅ **두 번째 Alert Policy 완료!**

---

## 완료 확인

다음 명령어로 생성된 Alert Policy를 확인:

```bash
gcloud alpha monitoring policies list \
    --project=kakao-webtoon-collector \
    --format="table(displayName,enabled)"
```

**예상 결과**:
- Pipeline Function Execution Failure
- Pipeline Scheduler Job Failure

---

## 테스트

> **⚠️ 중요**: Alert Policy 페이지에는 "TEST" 버튼이 없습니다! 실제 ERROR 로그를 발생시켜야 Alert가 트리거됩니다.

### 방법 1: Cloud Function 직접 호출 (가장 확실)

```bash
# Cloud Function URL 가져오기
FUNCTION_URL=$(gcloud functions describe pipeline-function \
    --gen2 \
    --region=asia-northeast3 \
    --project=kakao-webtoon-collector \
    --format='value(serviceConfig.uri)')

# 잘못된 요청으로 ERROR 발생
curl -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{"invalid":"request"}'
```

### 방법 2: Incidents 페이지에서 확인

Alert가 트리거되면 다음 페이지에 표시됩니다:

```
https://console.cloud.google.com/monitoring/alerting/incidents?project=kakao-webtoon-collector
```

### 알림 확인

1-2분 내에 두 이메일 주소(entrkjm@vaiv.kr, entrkjm@gmail.com)로 알림이 도착하는지 확인

---

## 🔧 문제 해결

### Alert가 트리거되지 않는 경우

1. **Duration 설정 확인** (가장 중요!):
   - Alert Policy 편집 → "Configure trigger" → Duration이 `1 minute`으로 설정되어 있는지 확인
   - Duration이 `0s`로 설정되어 있으면 Alert가 트리거되지 않을 수 있음
   - 수정 방법: Duration을 `1 minute`으로 변경 후 저장

2. **Alert Policy 활성화 확인**:
   ```bash
   gcloud alpha monitoring policies list \
       --project=kakao-webtoon-collector \
       --format="table(displayName,enabled)"
   ```

3. **필터 확인**:
   - `service_name`이 정확히 `pipeline-function`인지 확인
   - `resource.type`이 `cloud_run_revision`인지 확인
   - `severity = ERROR` 필터가 Metric labels에 추가되어 있는지 확인

4. **로그가 실제로 기록되었는지 확인**:
   - Cloud Logging에서 ERROR 로그 검색
   - 로그의 `resource.labels.service_name` 값 확인

### 이메일 알림이 오지 않는 경우

1. **알림 채널 확인**:
   ```bash
   gcloud alpha monitoring channels list \
       --project=kakao-webtoon-collector \
       --format="table(displayName,labels.email_address)"
   ```

2. **스팸 폴더 확인**

3. **Alert Policy의 알림 채널 설정 확인**:
   - Cloud Console에서 Alert Policy 편집
   - "Notifications" 섹션에서 알림 채널이 선택되어 있는지 확인

---

## 📚 참고

- [Alert Policy 테스트 가이드](./alert_test_guide.md)
- [네이버 프로젝트 Alert Policy 설정](../naver/docs/setup/alert_setup_complete_guide.md)
- [네이버 프로젝트 Alert Policy 수정 가이드](../naver/docs/setup/alert_policy_edit_guide.md) - 하나의 Policy에 여러 Condition 추가 방법
- [GCP Monitoring 문서](https://cloud.google.com/monitoring/alerts)

---

## 📝 중요 참고사항

### 실제 필터 형식

네이버 프로젝트의 실제 Alert Policy 필터 (작동 확인됨):
```
resource.type = "cloud_run_revision" 
AND resource.labels.service_name = "pipeline-function" 
AND metric.type = "logging.googleapis.com/log_entry_count" 
AND metric.labels.severity = "ERROR"
```

카카오 프로젝트도 네이버와 동일한 필터를 사용합니다.

### Filter Label 선택 가이드

Cloud Console UI에서 Filter를 추가할 때:
- **`service_name`** 또는 **`resource.labels.service_name`** 사용 (Resource labels 섹션)
- **`severity`** 또는 **`metric.labels.severity`** 사용 (Metric labels 섹션)
- 네이버 프로젝트에서도 동일한 필터를 사용하고 있으며 정상 작동합니다

### ⚠️ 중요: Cloud Run Revision을 직접 선택해야 합니다!

- Cloud Function Gen2는 실제로 **Cloud Run Revision** 리소스 타입을 사용합니다
- **"Cloud Function"을 선택하면 실패할 수 있으므로, 반드시 "Cloud Run Revision"을 직접 선택해야 합니다**
- 네이버 프로젝트에서도 "Cloud Function" 선택 시 실패했고, "Cloud Run Revision" 직접 선택 시 성공했습니다
- Filter는 `service_name` (Resource labels)과 `severity` (Metric labels)를 사용합니다

### Alert Policy 구조

**핵심**: 하나의 Alert Policy에 여러 개의 Filter를 추가합니다.

1. **Alert Policy 1**: Cloud Function 실행 실패
   - Filter 1: `service_name = pipeline-function` (Resource labels)
   - Filter 2: `severity = ERROR` (Metric labels)
   - 나중에 "+ Add alert condition"으로 `data-validation-function` Condition 추가 가능

2. **Alert Policy 2**: Cloud Scheduler 작업 실패
   - Filter 1: `job_id = kakao-webtoon-weekly-collection` (Resource labels)

### 알림 채널

**두 개의 이메일 채널 모두 선택 필수**:
- ✅ Pipeline Alert Email 1 (entrkjm@vaiv.kr)
- ✅ Pipeline Alert Email 2 (entrkjm@gmail.com)

---

**마지막 업데이트**: 2026-01-01
