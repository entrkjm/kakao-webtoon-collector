# Alert Policy 테스트 가이드 (카카오 웹툰 수집기)

> **목표**: Alert Policy가 정상 작동하는지 테스트하고 이메일 알림을 확인합니다.

---

## 📋 테스트 방법

### 방법 1: Cloud Console에서 테스트 로그 작성 (가장 간단)

#### 1단계: Cloud Logging 페이지 접속

1. 브라우저에서 다음 링크를 엽니다:
   ```
   https://console.cloud.google.com/logs/query?project=kakao-webtoon-collector
   ```

2. 또는 수동 접속:
   - [Google Cloud Console](https://console.cloud.google.com/) 접속
   - 프로젝트 선택: `kakao-webtoon-collector`
   - 왼쪽 메뉴: **"Logging"** → **"Logs Explorer"** 클릭

#### 2단계: 쿼리 작성

1. **"Query"** 또는 **"쿼리 작성"** 섹션에서 다음 쿼리를 입력:
   ```
   resource.type="cloud_run_revision"
   resource.labels.service_name="pipeline-function"
   ```

2. **"Run query"** 또는 **"쿼리 실행"** 버튼 클릭

3. 결과를 확인합니다 (로그가 표시되어야 함)

#### 3단계: 테스트 로그 작성 (간접 방법)

Cloud Console에서는 직접 로그를 작성할 수 없으므로, 다음 방법을 사용합니다:

**옵션 A: Cloud Function 직접 호출 (권장)**

1. Cloud Function URL 확인:
   ```bash
   gcloud functions describe pipeline-function \
       --gen2 \
       --region=asia-northeast3 \
       --project=kakao-webtoon-collector \
       --format="value(serviceConfig.uri)"
   ```

2. 잘못된 요청으로 호출:
   ```bash
   FUNCTION_URL="위에서 확인한 URL"
   curl -X POST "$FUNCTION_URL" \
       -H "Content-Type: application/json" \
       -d '{"invalid": "request", "date": "2099-01-01"}'
   ```

**옵션 B: gcloud logging write 사용 (간단)**

터미널에서 다음 명령어 실행:

```bash
# 프로젝트 설정
gcloud config set project kakao-webtoon-collector

# 테스트 ERROR 로그 작성
gcloud logging write test-error-log \
    "테스트 에러 메시지 - Alert Policy 테스트" \
    --severity=ERROR \
    --project=kakao-webtoon-collector
```

> **참고**: 이 방법은 기본 리소스 타입으로 로그를 작성하므로, Alert Policy의 필터와 정확히 일치하지 않을 수 있습니다.

**옵션 C: 실제 Cloud Function 실행 (가장 확실)**

Cloud Function이 배포되어 있다면, 실제로 잘못된 요청을 보내서 ERROR를 발생시킵니다:

```bash
# Cloud Function URL 가져오기
FUNCTION_URL=$(gcloud functions describe pipeline-function \
    --gen2 \
    --region=asia-northeast3 \
    --project=kakao-webtoon-collector \
    --format="value(serviceConfig.uri)")

# 잘못된 요청으로 ERROR 발생
curl -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{"date": "invalid-date"}'
```

---

## ✅ 확인 방법

### 1. Cloud Monitoring Incidents 확인

1. [Cloud Monitoring Incidents 페이지](https://console.cloud.google.com/monitoring/alerting/incidents?project=kakao-webtoon-collector) 접속

2. **"Incidents"** 탭에서 최근 생성된 Alert 확인

3. 약 1-2분 후 다음 정보가 표시되어야 합니다:
   - **Alert Policy**: Pipeline Function Execution Failure
   - **Status**: Firing (또는 Open)
   - **Severity**: ERROR

### 2. 이메일 알림 확인

약 1-2분 후 다음 이메일 주소로 알림이 도착하는지 확인:

- ✅ **entrkjm@vaiv.kr**
- ✅ **entrkjm@gmail.com**

이메일 제목 예시:
```
[Alert] Pipeline Function Execution Failure
```

### 3. 로그 확인

Cloud Logging에서 ERROR 로그가 기록되었는지 확인:

```bash
gcloud logging read \
    --limit=5 \
    --format="table(timestamp,severity,textPayload)" \
    --project=kakao-webtoon-collector \
    --filter='severity="ERROR"'
```

---

## 🔧 문제 해결

### Alert가 트리거되지 않는 경우

1. **Alert Policy 활성화 확인**:
   ```bash
   gcloud alpha monitoring policies list \
       --project=kakao-webtoon-collector \
       --format="table(displayName,enabled)"
   ```

2. **필터 확인**:
   - `service_name`이 정확히 `pipeline-function`인지 확인
   - `resource.type`이 `cloud_run_revision`인지 확인
   - `severity` 필터는 사용하지 않습니다 (작동하지 않음)

3. **로그가 실제로 기록되었는지 확인**:
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

## 📝 테스트 체크리스트

- [ ] Cloud Function URL 확인
- [ ] 테스트 ERROR 로그 작성 (또는 잘못된 요청으로 Cloud Function 호출)
- [ ] 1-2분 대기
- [ ] Cloud Monitoring Incidents에서 Alert 확인
- [ ] 이메일 알림 확인 (entrkjm@vaiv.kr, entrkjm@gmail.com)

---

## 🎯 빠른 테스트 스크립트

다음 스크립트를 실행하면 자동으로 테스트를 수행합니다:

```bash
#!/bin/bash
# Alert Policy 테스트 스크립트

PROJECT_ID="kakao-webtoon-collector"
FUNCTION_NAME="pipeline-function"
REGION="asia-northeast3"

echo "=== Alert Policy 테스트 시작 ==="

# 1. Cloud Function URL 가져오기
echo "1. Cloud Function URL 확인 중..."
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
    --gen2 \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(serviceConfig.uri)" 2>/dev/null)

if [ -z "$FUNCTION_URL" ]; then
    echo "❌ Cloud Function을 찾을 수 없습니다."
    echo "   Cloud Function이 배포되어 있는지 확인하세요."
    exit 1
fi

echo "✅ Cloud Function URL: $FUNCTION_URL"

# 2. 잘못된 요청으로 ERROR 발생
echo ""
echo "2. 테스트 ERROR 발생 중..."
curl -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{"date": "invalid-date", "sort_keys": ["invalid"]}' \
    -s -o /dev/null

echo "✅ 테스트 요청 전송 완료"

# 3. 안내
echo ""
echo "=== 다음 단계 ==="
echo "1. 약 1-2분 후 Cloud Monitoring Incidents 확인:"
echo "   https://console.cloud.google.com/monitoring/alerting/incidents?project=$PROJECT_ID"
echo ""
echo "2. 이메일 알림 확인:"
echo "   - entrkjm@vaiv.kr"
echo "   - entrkjm@gmail.com"
```

---

**마지막 업데이트**: 2026-01-01

