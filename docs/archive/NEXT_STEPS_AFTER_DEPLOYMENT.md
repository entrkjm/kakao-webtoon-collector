# 배포 후 다음 단계

> **작성일**: 2026-01-01  
> **현재 상태**: GCP 배포 완료 ✅

---

## ✅ 완료된 작업

- [x] GCP 프로젝트 생성 (`kakao-webtoon-collector`)
- [x] 결제 계정 연결
- [x] 인프라 설정 (GCS, BigQuery, 서비스 계정)
- [x] Cloud Functions 배포 (`pipeline_function`)
- [x] Cloud Scheduler 설정 (매주 월요일 오전 9시)

---

## 🎯 다음 단계 (우선순위 순)

### 1. 실제 데이터 수집 테스트 (필수) ⭐

**목표**: 배포된 파이프라인이 실제로 데이터를 수집하고 저장하는지 확인

**작업 내용**:

#### 1.1 수동 실행 테스트

```bash
# 함수 URL 확인
FUNCTION_URL=$(gcloud functions describe pipeline_function \
  --gen2 \
  --region=asia-northeast3 \
  --format="value(serviceConfig.uri)")

# 테스트 요청 (단일 정렬 옵션)
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-01-01",
    "sort_keys": ["popularity"],
    "collect_all_weekdays": false
  }'

# 또는 모든 정렬 옵션 테스트
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-01-01",
    "sort_keys": ["popularity", "views", "createdAt", "popularityMale", "popularityFemale"],
    "collect_all_weekdays": false
  }'
```

**확인 사항**:
- [ ] HTTP 200 응답 확인
- [ ] 응답 본문에 `"status": "success"` 확인
- [ ] Cloud Functions 로그에서 에러 없음 확인

#### 1.2 GCS 데이터 확인

```bash
# 업로드된 파일 확인
gsutil ls -r gs://kakao-webtoon-raw/raw_data/

# 특정 날짜 파일 확인
gsutil ls gs://kakao-webtoon-raw/raw_data/2026-01-01/

# 파일 내용 확인 (JSON)
gsutil cat gs://kakao-webtoon-raw/raw_data/2026-01-01/webtoon_chart.json | head -50
```

**확인 사항**:
- [ ] JSON 파일이 업로드되었는지 확인
- [ ] 날짜별 디렉터리 구조 확인
- [ ] 정렬별 파일이 생성되었는지 확인 (sort_key가 있는 경우)

#### 1.3 BigQuery 데이터 확인

```sql
-- 데이터 수 확인
SELECT 
  chart_date,
  COUNT(DISTINCT webtoon_id) AS webtoon_count,
  COUNT(*) AS total_records
FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
GROUP BY chart_date
ORDER BY chart_date DESC
LIMIT 10;

-- dim_webtoon 확인
SELECT COUNT(*) AS total_webtoons
FROM `kakao-webtoon-collector.kakao_webtoon.dim_webtoon`;

-- 특정 날짜의 상위 10개 웹툰 확인
SELECT 
  w.title,
  w.author,
  c.rank,
  c.sort_key,
  c.view_count
FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart` c
JOIN `kakao-webtoon-collector.kakao_webtoon.dim_webtoon` w
  ON c.webtoon_id = w.webtoon_id
WHERE c.chart_date = '2026-01-01'
  AND c.sort_key = 'popularity'
ORDER BY c.rank
LIMIT 10;
```

**확인 사항**:
- [ ] `fact_weekly_chart` 테이블에 데이터가 저장되었는지 확인
- [ ] `dim_webtoon` 테이블에 웹툰 정보가 저장되었는지 확인
- [ ] 정렬 옵션별로 데이터가 다르게 저장되었는지 확인
- [ ] 레코드 수가 예상과 일치하는지 확인

#### 1.4 멱등성 테스트

같은 날짜로 다시 실행하여 중복 데이터가 생성되지 않는지 확인:

```bash
# 같은 날짜로 재실행
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-01-01",
    "sort_keys": ["popularity"],
    "collect_all_weekdays": false
  }'

# BigQuery에서 레코드 수 확인 (변경 없어야 함)
```

**확인 사항**:
- [ ] 재실행 후 레코드 수가 증가하지 않음
- [ ] MERGE 작업이 정상적으로 작동함

**예상 시간**: 30분-1시간

---

### 2. Alert Policy 설정 (권장) ⚠️

**목표**: 파이프라인 실패 시 알림 받기

**작업 내용**:

#### 2.1 알림 채널 생성

GCP 콘솔에서:
1. [Cloud Monitoring > 알림](https://console.cloud.google.com/monitoring/alerting?project=kakao-webtoon-collector) 접속
2. "알림 채널" → "알림 채널 만들기"
3. 이메일 주소 추가 (예: entrkjm@gmail.com)

#### 2.2 Alert Policy 생성

**정책 이름**: "Pipeline Function Execution Failure"

**조건**:
- 리소스 타입: Cloud Function
- 메트릭: `cloudfunctions.googleapis.com/function/execution_count`
- 필터: `function_name="pipeline_function"` AND `severity="ERROR"`

**알림 채널**: 위에서 생성한 이메일 채널

**참고**: 네이버 프로젝트의 Alert Policy 설정 참고
- `naver/docs/setup/alert_setup_complete_guide.md`

**예상 시간**: 10-15분

---

### 3. 데이터 검증 함수 배포 (선택사항)

**목표**: 데이터 품질 자동 검증

**작업 내용**:

네이버 프로젝트의 `data_validation_function`을 참고하여 구현:

```bash
# 네이버 프로젝트 참고
ls naver/functions/data_validation_function/
```

**기능**:
- 중복 레코드 검증
- Foreign Key 관계 검증
- 필수 필드 검증
- 데이터 일관성 검증

**예상 시간**: 2-3시간 (구현 필요)

---

### 4. Cloud Scheduler 수동 실행 테스트 (권장)

**목표**: 스케줄러가 정상 작동하는지 확인

**작업 내용**:

```bash
# Scheduler 작업 수동 실행
gcloud scheduler jobs run kakao-webtoon-weekly-collection \
  --location=asia-northeast3

# 실행 후 로그 확인
gcloud functions logs read pipeline_function \
  --gen2 \
  --region=asia-northeast3 \
  --limit=50
```

**확인 사항**:
- [ ] 작업이 성공적으로 실행됨
- [ ] Cloud Functions가 정상적으로 호출됨
- [ ] 데이터가 정상적으로 수집됨

**예상 시간**: 10분

---

### 5. 모니터링 대시보드 생성 (선택사항)

**목표**: 파이프라인 상태를 한눈에 확인

**작업 내용**:

```bash
# 네이버 프로젝트 참고
./scripts/monitoring/create_monitoring_dashboard.sh
```

**대시보드 항목**:
- 함수 실행 횟수
- 함수 실행 시간
- 에러 발생 횟수
- 데이터 수집량

**예상 시간**: 15-20분

---

### 6. GitHub Actions CI/CD 설정 (선택사항)

**목표**: 코드 변경 시 자동 배포

**작업 내용**:

네이버 프로젝트의 GitHub Actions 설정 참고:
- `naver/.github/workflows/deploy.yml`
- `naver/docs/setup/github_actions_setup.md`

**예상 시간**: 30분-1시간

---

## 📋 체크리스트

### 필수 작업
- [ ] 실제 데이터 수집 테스트
- [ ] GCS 데이터 확인
- [ ] BigQuery 데이터 확인
- [ ] 멱등성 테스트

### 권장 작업
- [ ] Alert Policy 설정
- [ ] Cloud Scheduler 수동 실행 테스트

### 선택 작업
- [ ] 데이터 검증 함수 배포
- [ ] 모니터링 대시보드 생성
- [ ] GitHub Actions CI/CD 설정

---

## 🚀 빠른 시작

가장 중요한 다음 단계는 **실제 데이터 수집 테스트**입니다:

```bash
# 1. 함수 URL 확인
FUNCTION_URL=$(gcloud functions describe pipeline_function \
  --gen2 \
  --region=asia-northeast3 \
  --format="value(serviceConfig.uri)")

# 2. 테스트 실행
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-01-01", "sort_keys": ["popularity"]}'

# 3. BigQuery에서 데이터 확인
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart\`"
```

---

## 📚 관련 문서

- [배포 체크리스트](DEPLOYMENT_CHECKLIST.md)
- [GCP 설정 가이드](GCP_SETUP_GUIDE.md)
- [네이버 프로젝트 Alert Policy 설정](../naver/docs/setup/alert_setup_complete_guide.md) (참고)

---

**마지막 업데이트**: 2026-01-01

