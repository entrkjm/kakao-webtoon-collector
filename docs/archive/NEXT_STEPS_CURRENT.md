# 카카오 웹툰 수집기 - 현재 상태 및 다음 단계

> **작성일**: 2026-01-01  
> **현재 상태**: 배포 완료 + 데이터 수집 테스트 완료 ✅

---

## ✅ 완료된 작업

### 1. 배포 및 인프라
- [x] GCP 프로젝트 생성 (`kakao-webtoon-collector`)
- [x] 결제 계정 연결
- [x] 인프라 설정 (GCS, BigQuery, 서비스 계정)
- [x] Cloud Functions 배포 (`pipeline_function`)
- [x] Cloud Scheduler 설정 (매주 월요일 오전 9시)

### 2. 데이터 수집 테스트
- [x] 실제 데이터 수집 테스트 완료
- [x] `weekday`, `sort_key`, `view_count` NULL 문제 해결
- [x] 모든 요일 데이터 수집 확인 (1,044개 레코드, 1,031개 고유 웹툰)
- [x] GCS 업로드 확인
- [x] BigQuery 데이터 저장 확인

### 3. 버그 수정
- [x] `weekday` 추출 로직 수정 (최상위 레벨 + data_item 레벨 모두 확인)
- [x] `sort_key` 파라미터 추가 및 전달
- [x] `view_count` 추출 로직 수정 (sorting.views 사용)
- [x] BigQuery 데이터 타입 변환 수정

---

## 🎯 다음 단계 (우선순위 순)

### 1. Alert Policy 설정 (필수) ⚠️

**목표**: 파이프라인 실패 시 이메일 알림 받기

**작업 내용**:

#### 1.1 알림 채널 생성

GCP 콘솔에서:
1. [Cloud Monitoring > 알림](https://console.cloud.google.com/monitoring/alerting?project=kakao-webtoon-collector) 접속
2. "알림 채널" → "알림 채널 만들기"
3. 이메일 주소 추가 (예: entrkjm@gmail.com)

#### 1.2 Alert Policy 생성

**정책 이름**: "Pipeline Function Execution Failure"

**조건**:
- 리소스 타입: Cloud Function
- 메트릭: `Log entry count`
- 필터:
  - `function_name = pipeline-function`
  - `severity = ERROR`
- Threshold: `Any value is above 0`
- Duration: `1 minute`

**알림 채널**: 위에서 생성한 이메일 채널

**참고**: 네이버 프로젝트의 Alert Policy 설정 참고
- `naver/docs/setup/alert_setup_complete_guide.md`

**예상 시간**: 10-15분

---

### 2. 이전 NULL 데이터 정리 (선택사항)

**목표**: 2026-01-01 날짜의 NULL 데이터 정리

**현재 상태**:
- 2026-01-01: 1,187개 레코드 (NULL 데이터 포함)
- 2026-01-02: 1,044개 레코드 (정상 데이터)

**작업 내용**:

```sql
-- NULL 데이터 삭제
DELETE FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE chart_date = '2026-01-01'
  AND (weekday IS NULL OR sort_key IS NULL);
```

또는 해당 날짜 데이터를 다시 수집:

```bash
FUNCTION_URL=$(gcloud functions describe pipeline_function --gen2 --region=asia-northeast3 --format="value(serviceConfig.uri)")
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-01-01", "sort_keys": ["popularity", "views", "createdAt", "popularityMale", "popularityFemale"], "collect_all_weekdays": true}'
```

**예상 시간**: 5-10분

---

### 3. Cloud Scheduler 수동 실행 테스트 (권장)

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

### 4. 데이터 검증 함수 배포 (선택사항)

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
- [x] 실제 데이터 수집 테스트
- [x] GCS 데이터 확인
- [x] BigQuery 데이터 확인
- [x] NULL 값 문제 해결
- [ ] Alert Policy 설정 ⭐ **다음 단계**

### 권장 작업
- [ ] Cloud Scheduler 수동 실행 테스트
- [ ] 이전 NULL 데이터 정리

### 선택 작업
- [ ] 데이터 검증 함수 배포
- [ ] 모니터링 대시보드 생성
- [ ] GitHub Actions CI/CD 설정

---

## 🚀 빠른 시작

가장 중요한 다음 단계는 **Alert Policy 설정**입니다:

1. [Cloud Monitoring Alerting 페이지](https://console.cloud.google.com/monitoring/alerting?project=kakao-webtoon-collector) 접속
2. 알림 채널 생성 (이메일)
3. Alert Policy 생성 (ERROR 로그 감지)

**참고 가이드**: `naver/docs/setup/alert_setup_complete_guide.md`

---

## 📊 현재 데이터 상태

### 2026-01-02 (정상 데이터)
- 총 레코드: 1,044개
- 고유 웹툰: 1,031개
- 요일별 분포:
  - mon: 148개
  - tue: 151개
  - wed: 139개
  - thu: 147개
  - fri: 169개
  - sat: 153개
  - sun: 137개
- NULL 값: 0개 (모든 필드 정상)

### 2026-01-01 (일부 NULL 데이터 포함)
- 총 레코드: 1,187개 (NULL 데이터 포함)
- 정상 데이터: 148개 (mon, popularity)
- NULL 데이터: 1,039개 (정리 필요)

---

**마지막 업데이트**: 2026-01-01

