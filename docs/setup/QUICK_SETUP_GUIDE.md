# 빠른 설정 가이드

> **목적**: 남은 설정 작업을 빠르게 완료하기 위한 가이드

---

## 📋 설정 체크리스트

### 1. GitHub Secrets 설정 (필수)

#### 1.1 GCP 서비스 계정 키 생성

터미널에서 다음 명령어 실행:

```bash
gcloud iam service-accounts keys create ~/gcp-sa-key.json \
    --iam-account=webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com \
    --project=kakao-webtoon-collector
```

#### 1.2 키 파일 내용 복사

**macOS:**
```bash
cat ~/gcp-sa-key.json | pbcopy
```

**Linux:**
```bash
cat ~/gcp-sa-key.json | xclip -selection clipboard
```

#### 1.3 GitHub Secrets에 등록

1. GitHub 저장소 접속
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **"New repository secret"** 클릭
4. **Name**: `GCP_SA_KEY`
5. **Secret**: (복사한 키 파일 내용 붙여넣기)
6. **"Add secret"** 클릭

#### 1.4 (선택) 이메일 알림 설정

1. **"New repository secret"** 클릭
2. **Name**: `NOTIFICATION_CHANNEL_EMAIL`
3. **Secret**: `your-email@example.com`
4. **"Add secret"** 클릭

**완료 후**: 키 파일 삭제 (보안)
```bash
rm ~/gcp-sa-key.json
```

---

### 2. 모니터링 대시보드 생성

#### 2.1 대시보드 페이지 접속

[대시보드 생성 링크](https://console.cloud.google.com/monitoring/dashboards?project=kakao-webtoon-collector)

#### 2.2 대시보드 생성

1. **"CREATE DASHBOARD"** 클릭
2. 대시보드 이름: **"Kakao Webtoon Pipeline Dashboard"**

#### 2.3 위젯 추가

**위젯 1: Pipeline Function 실행 횟수**
1. **"Add widget"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Run Revision"** 선택
4. Metric: **"Request count"** 선택
5. 필터 추가:
   - **"Add filter"** 클릭
   - **"service_name"** 선택
   - 값: `pipeline-function` 입력
6. **"Apply"** 클릭

**위젯 2: Pipeline Function 실행 시간**
1. **"Add widget"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Run Revision"** 선택
4. Metric: **"Request latencies"** 선택
5. 필터 추가:
   - **"Add filter"** 클릭
   - **"service_name"** 선택
   - 값: `pipeline-function` 입력
6. **"Apply"** 클릭

**위젯 3: Pipeline Function 에러 발생 횟수**
1. **"Add widget"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Run Revision"** 선택
4. Metric: **"Request count"** 선택
5. 필터 추가:
   - **"Add filter"** 클릭
   - **"service_name"** 선택
   - 값: `pipeline-function` 입력
   - **"Add filter"** 클릭 (추가)
   - **"response_code"** 선택
   - 연산자: `>=` 선택
   - 값: `400` 입력
6. **"Apply"** 클릭

**위젯 4: Cloud Scheduler 작업 실행 횟수**
1. **"Add widget"** 클릭
2. **"Select a metric"** 클릭
3. 리소스: **"Cloud Scheduler Job"** 선택
4. Metric: **"Execution count"** 선택
5. 필터 추가:
   - **"Add filter"** 클릭
   - **"job_id"** 선택
   - 값: `kakao-webtoon-weekly-collection` 입력
6. **"Apply"** 클릭

#### 2.4 저장

1. 모든 위젯 추가 완료 후 **"SAVE"** 버튼 클릭
2. 대시보드 이름 확인
3. **"SAVE"** 클릭

---

## ✅ 완료 확인

### GitHub Actions 확인

1. GitHub 저장소 → **Actions** 탭
2. **"Deploy Cloud Functions"** 워크플로우가 보이는지 확인
3. (선택) **"Run workflow"**로 수동 테스트

### 대시보드 확인

1. [대시보드 페이지](https://console.cloud.google.com/monitoring/dashboards?project=kakao-webtoon-collector) 접속
2. **"Kakao Webtoon Pipeline Dashboard"** 확인
3. 4개의 위젯이 정상적으로 표시되는지 확인

---

## 📚 상세 가이드

- **GitHub Actions**: `kakao/docs/setup/github_actions_setup.md`
- **모니터링 대시보드**: `kakao/docs/monitoring/monitoring_dashboard_step_by_step.md`

---

**마지막 업데이트**: 2026-01-01

