# 카카오 웹툰 수집기 - 다음 단계

> **작성일**: 2026-01-01  
> **현재 상태**: Alert Policy 설정 완료 ✅

---

## ✅ 완료된 작업

### 1. 배포 및 인프라
- [x] GCP 프로젝트 생성 (`kakao-webtoon-collector`)
- [x] 결제 계정 연결
- [x] 인프라 설정 (GCS, BigQuery, 서비스 계정)
- [x] Cloud Functions 배포 (`pipeline-function`)
- [x] Cloud Scheduler 설정 (매주 월요일 오전 9시)

### 2. 데이터 수집 및 검증
- [x] 실제 데이터 수집 테스트 완료
- [x] 모든 요일 데이터 수집 확인
- [x] 모든 정렬 옵션 수집 확인
- [x] GCS 업로드 확인
- [x] BigQuery 데이터 저장 확인

### 3. 모니터링 및 알림
- [x] Alert Policy 설정 완료 (2개)
  - [x] Pipeline Function Execution Failure
  - [x] Pipeline Scheduler Job Failure
- [x] Alert 정상 작동 확인

### 4. 문서 정리
- [x] 문서 체계적 정리 완료

---

## 🎯 다음 단계 (우선순위 순)

### 1. GitHub Secrets 설정 (필수)

**목표**: GitHub Actions 자동 배포 활성화

**작업 내용**:
1. GCP 서비스 계정 키 생성
2. GitHub Secrets에 `GCP_SA_KEY` 등록
3. (선택) `NOTIFICATION_CHANNEL_EMAIL` 등록

**예상 시간**: 5분

**참고**: `kakao/docs/setup/github_actions_setup.md`

---

### 2. 모니터링 대시보드 완료 ✅ 거의 완료

**목표**: 파이프라인 상태를 한눈에 확인

**완료 내용**:
- [x] 대시보드 생성
- [x] 위젯 추가 (진행 중)
- [ ] 대시보드 저장

**참고**: `kakao/docs/monitoring/monitoring_dashboard_step_by_step.md`

---

### 3. 데이터 검증 함수 스케줄링 ✅ 완료

**목표**: 주기적으로 데이터 품질 검증

**완료 내용**:
- [x] Cloud Scheduler 작업 생성: `data-validation-scheduler`
- [x] 스케줄: 매주 월요일 오전 10시 (수집 후 1시간)
- [x] 다음 실행: 2026-01-05T01:00:00Z

**참고**: `kakao/scripts/setup/setup_data_validation_scheduler.sh`

---

### 4. 정기적인 데이터 확인 (운영)

**목표**: 파이프라인 상태를 한눈에 확인

**완료 내용**:
- [x] 대시보드 생성: `kakao-webtoon-pipeline`
- [x] 위젯 4개 추가:
  - Pipeline Function 실행 횟수
  - Pipeline Function 실행 시간
  - Pipeline Function 에러 발생 횟수
  - Cloud Scheduler 작업 실행 횟수

**참고**: 
- `kakao/scripts/monitoring/create_monitoring_dashboard.sh`
- `kakao/docs/monitoring/monitoring_dashboard_guide.md`

---

### 5. GitHub Actions CI/CD 설정 ✅ 완료 (Secrets 설정 필요)

**목표**: 코드 변경 시 자동 배포

**완료 내용**:
- [x] GitHub Actions 워크플로우 생성: `.github/workflows/deploy.yml`
- [x] 설정 가이드 작성: `docs/setup/github_actions_setup.md`
- [x] 자동 배포 설정 완료 (main 브랜치 push 시)

**다음 단계**:
1. GCP 서비스 계정 키 생성
2. GitHub Secrets에 `GCP_SA_KEY` 등록
3. (선택) `NOTIFICATION_CHANNEL_EMAIL` 등록

**참고**: `kakao/docs/setup/github_actions_setup.md`

---

### 4. 정기적인 데이터 확인 (운영)

**목표**: 데이터 수집이 정상적으로 진행되는지 확인

**작업 내용**:

1. **주간 데이터 확인**:
   - BigQuery에서 최신 데이터 확인
   - 데이터 품질 검증

2. **비용 모니터링**:
   - GCP Always Free Tier 사용량 확인
   - 비용 초과 방지

**예상 시간**: 주 1회 10분

---

## 📋 체크리스트

### 필수 작업
- [x] Alert Policy 설정 ✅ **완료**

### 권장 작업
- [x] 데이터 검증 함수 스케줄링 ✅ **완료**
- [x] 모니터링 대시보드 생성 ✅ **완료**

### 선택 작업
- [x] GitHub Actions CI/CD 설정 ✅ **완료** (Secrets 설정 필요)
- [ ] 정기적인 데이터 확인

---

## 🚀 빠른 시작

가장 권장되는 다음 단계는 **데이터 검증 함수 스케줄링**입니다:

1. 데이터 검증 함수가 배포되어 있는지 확인
2. Cloud Scheduler에 검증 작업 추가
3. 검증 결과 확인

---

## 📚 관련 문서

- [Alert Policy 최종 설정](./setup/alert_final_configuration.md)
- [Alert Policy 설정 가이드](./setup/alert_setup_guide.md)
- [GCP 설정 가이드](./setup/GCP_SETUP_GUIDE.md)
- [배포 체크리스트](./setup/DEPLOYMENT_CHECKLIST.md)

---

**마지막 업데이트**: 2026-01-01

