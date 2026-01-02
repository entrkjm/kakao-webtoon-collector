# 카카오 웹툰 수집기 - 최종 다음 단계

> **작성일**: 2026-01-01  
> **현재 상태**: 모든 정렬 옵션 수집 확인 완료 ✅

---

## ✅ 완료된 작업

### 1. 배포 및 인프라
- [x] GCP 프로젝트 생성 (`kakao-webtoon-collector`)
- [x] 결제 계정 연결
- [x] 인프라 설정 (GCS, BigQuery, 서비스 계정)
- [x] Cloud Functions 배포 (`pipeline_function`)
- [x] Cloud Scheduler 설정 (매주 월요일 오전 9시)

### 2. 데이터 수집 및 검증
- [x] 실제 데이터 수집 테스트 완료
- [x] `weekday`, `sort_key`, `view_count` NULL 문제 해결
- [x] 모든 요일 데이터 수집 확인 (7개 요일)
- [x] **모든 정렬 옵션 수집 확인 (5개 정렬)** ✅
- [x] 정렬별 rank 차이 확인 완료
- [x] GCS 업로드 확인
- [x] BigQuery 데이터 저장 확인

### 3. 데이터 품질 관리
- [x] NULL 데이터 정리 (2026-01-01)
- [x] 데이터 검증 함수 배포 (`data-validation-function`)
- [x] Cloud Scheduler 설정 업데이트 (`collect_all_weekdays: true`)

---

## 🎯 다음 단계 (우선순위 순)

### 1. Alert Policy 설정 (필수) ⚠️

**목표**: 파이프라인 실패 시 이메일 알림 받기

**작업 내용**:

#### 1.1 알림 채널 생성

1. [Cloud Monitoring > 알림](https://console.cloud.google.com/monitoring/alerting?project=kakao-webtoon-collector) 접속
2. "알림 채널" → "알림 채널 만들기"
3. 이메일 주소 추가 (예: entrkjm@gmail.com)
4. "만들기" 클릭

#### 1.2 Alert Policy 생성

**3개 Alert Policy 생성 필요**:

1. **Pipeline Function Execution Failure**
   - Cloud Function `pipeline-function`의 ERROR 로그 감지

2. **Pipeline Scheduler Job Failure**
   - Cloud Scheduler `kakao-webtoon-weekly-collection` 작업 실패 감지

3. **Data Validation Function Failure**
   - Cloud Function `data-validation-function`의 ERROR 로그 감지

**상세 가이드**: `kakao/docs/setup/alert_setup_guide.md` 참고

**예상 시간**: 15-20분

---

### 2. Cloud Scheduler 수동 실행 테스트 (권장)

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
- [ ] 모든 정렬 옵션(5개) 데이터가 수집됨
- [ ] 모든 요일(7개) 데이터가 수집됨
- [ ] BigQuery에 데이터가 저장됨

**예상 시간**: 10분

---

### 3. 데이터 검증 함수 스케줄링 (선택사항)

**목표**: 데이터 검증 함수를 주기적으로 실행

**작업 내용**:

```bash
# 데이터 검증 함수 URL 확인
VALIDATION_URL=$(gcloud functions describe data-validation-function \
  --gen2 \
  --region=asia-northeast3 \
  --format="value(serviceConfig.uri)")

# Cloud Scheduler 작업 생성 (매주 화요일 오전 10시)
gcloud scheduler jobs create http data-validation-check \
  --location=asia-northeast3 \
  --schedule="0 1 * * 2" \
  --time-zone="Asia/Seoul" \
  --uri="$VALIDATION_URL" \
  --http-method=POST \
  --message-body='{"date": null}' \
  --description="카카오 웹툰 데이터 검증 (매주 화요일 오전 10시)" \
  --attempt-deadline=600s
```

**예상 시간**: 5분

---

### 4. 모니터링 대시보드 생성 (선택사항)

**목표**: 파이프라인 상태를 한눈에 확인

**작업 내용**:

네이버 프로젝트의 모니터링 대시보드 스크립트 참고:
- `naver/scripts/monitoring/create_monitoring_dashboard.sh`

**대시보드 항목**:
- 함수 실행 횟수
- 함수 실행 시간
- 에러 발생 횟수
- 데이터 수집량 (정렬별, 요일별)
- 데이터 검증 결과

**예상 시간**: 15-20분

---

### 5. GitHub Actions CI/CD 설정 (선택사항)

**목표**: 코드 변경 시 자동 배포

**작업 내용**:

네이버 프로젝트의 GitHub Actions 설정 참고:
- `naver/.github/workflows/deploy.yml`
- `naver/docs/setup/github_actions_setup.md`

**예상 시간**: 30분-1시간

---

## 📋 체크리스트

### 필수 작업
- [ ] Alert Policy 설정 ⭐ **다음 단계**
  - [ ] 알림 채널 생성
  - [ ] Pipeline Function Execution Failure 정책 생성
  - [ ] Pipeline Scheduler Job Failure 정책 생성
  - [ ] Data Validation Function Failure 정책 생성

### 권장 작업
- [ ] Cloud Scheduler 수동 실행 테스트
- [ ] 데이터 검증 함수 스케줄링

### 선택 작업
- [ ] 모니터링 대시보드 생성
- [ ] GitHub Actions CI/CD 설정

---

## 🚀 빠른 시작

가장 중요한 다음 단계는 **Alert Policy 설정**입니다:

1. [Cloud Monitoring Alerting 페이지](https://console.cloud.google.com/monitoring/alerting?project=kakao-webtoon-collector) 접속
2. 알림 채널 생성 (이메일)
3. Alert Policy 생성 (3개)
   - 가이드 참고: `kakao/docs/setup/alert_setup_guide.md`

---

## 📊 현재 데이터 상태

### 2026-01-03 (완전한 데이터)
- 총 레코드: 5,220개 (1,044개 × 5개 정렬 옵션)
- 고유 웹툰: 1,031개
- 정렬 옵션: 5개 (popularity, views, createdAt, popularityMale, popularityFemale)
- 요일: 7개 (mon, tue, wed, thu, fri, sat, sun)
- NULL 값: 0개 (모든 필드 정상)

### 정렬별 rank 차이 확인
- 같은 웹툰이 정렬 옵션에 따라 다른 rank를 가짐
- 예: "데드맨31"
  - popularity: 1위
  - views: 2위
  - createdAt: 5위
  - popularityMale: 2위
  - popularityFemale: 1위

---

## 📚 관련 문서

- [Alert Policy 설정 가이드](setup/alert_setup_guide.md)
- [GCP 설정 가이드](setup/GCP_SETUP_GUIDE.md)
- [배포 체크리스트](setup/DEPLOYMENT_CHECKLIST.md)
- [데이터 검증 함수 README](../functions/data_validation_function/README.md)

---

**마지막 업데이트**: 2026-01-01

