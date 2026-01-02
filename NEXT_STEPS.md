# 카카오 웹툰 수집기 - 다음 단계

## ✅ 완료된 작업

1. **로컬 파이프라인 구현**
   - ✅ API 엔드포인트 발견 및 구현
   - ✅ 데이터 모델 정의 (dim_webtoon, fact_weekly_chart)
   - ✅ Extract → Parse → Transform 파이프라인 구현
   - ✅ 작가 정보 추출
   - ✅ 모든 요일 데이터 수집 기능
   - ✅ 정렬 옵션별 수집 (클라이언트 사이드 정렬 반영)
   - ✅ 멱등성 보장 (중복 실행 테스트 완료)

2. **API 및 데이터 구조 분석**
   - ✅ API 엔드포인트 발견: `https://gateway-kw.kakao.com/section/v2/timetables/days`
   - ✅ 정렬 정보 확인: 각 카드의 `sorting` 객체 사용
   - ✅ 데이터 구조 파악 완료

---

## 🎯 다음 단계 (우선순위 순)

### ✅ 1. GCS/BigQuery 연동 모듈 구현 (완료)

**완료된 작업**:
- ✅ `src/upload_gcs.py` 구현
- ✅ `src/upload_bigquery.py` 구현
- ✅ 환경 변수로 업로드 제어

---

### ✅ 2. Cloud Functions 배포 구조 생성 (완료)

**완료된 작업**:
- ✅ `functions/pipeline_function/main.py` 구현
- ✅ `functions/pipeline_function/requirements.txt` 작성
- ✅ `functions/pipeline_function/deploy.sh` 작성
- ✅ `functions/pipeline_function/test_local.py` 작성
- ✅ 로컬 테스트 성공

---

### ✅ 3. 로컬 Functions Framework 테스트 (완료)

**완료된 작업**:
- ✅ 로컬 Functions Framework 테스트 성공
- ✅ GCS/BigQuery 모듈 없이도 작동하도록 수정

---

### 4. GCP 인프라 설정 (다음 단계)

**목표**: GCP 프로젝트 및 리소스 생성

**작업 내용**:
- [ ] GCP 프로젝트 생성 또는 기존 프로젝트 사용 결정
- [ ] 인프라 자동 설정 스크립트 실행
  ```bash
  cd scripts/setup
  ./setup_gcp_prerequisites.sh
  ```
  - GCS 버킷 생성 (`kakao-webtoon-raw`)
  - BigQuery 데이터셋 및 테이블 생성
  - 서비스 계정 생성 및 권한 설정

**생성된 파일**:
- ✅ `scripts/setup/setup_gcp_prerequisites.sh` - 자동 설정 스크립트
- ✅ `scripts/setup/setup_bigquery.sql` - BigQuery 스키마
- ✅ `docs/setup/GCP_SETUP_GUIDE.md` - 설정 가이드

**예상 시간**: 30분-1시간

---

### 5. Cloud Functions 배포 및 테스트 (필수)

**목표**: 실제 GCP 환경에서 배포 및 테스트

**작업 내용**:
- [ ] Cloud Functions 배포
  - `gcloud functions deploy` 실행
  - 환경 변수 설정 확인
  
- [ ] 수동 HTTP 트리거 테스트
  - Cloud Console에서 직접 호출
  - 또는 `curl` 명령어로 테스트
  
- [ ] GCS 업로드 확인
- [ ] BigQuery 데이터 적재 확인
- [ ] 멱등성 테스트 (같은 날짜 재실행)

**예상 시간**: 1-2시간

---

### 6. Cloud Scheduler 설정 (필수)

**목표**: 주 1회 자동 실행 설정

**작업 내용**:
- [ ] Cloud Scheduler 작업 생성
  - 작업명: `kakao-webtoon-weekly-collection`
  - 스케줄: 매주 월요일 오전 9시 (또는 적절한 시간)
  - HTTP 트리거로 Cloud Functions 호출
  
- [ ] 테스트 실행 확인

**참고 파일**:
- `naver/scripts/setup/setup_scheduler.sh`

**예상 시간**: 30분-1시간

---

### 7. GitHub Actions CI/CD 구축 (권장)

**목표**: 코드 변경 시 자동 배포

**작업 내용**:
- [ ] `.github/workflows/deploy.yml` 작성
  - 코드 푸시 시 자동 배포
  - 테스트 실행
  
- [ ] GitHub 저장소 설정
  - Git 저장소 초기화 (아직 안 됨)
  - GitHub Actions 시크릿 설정

**참고 파일**:
- `naver/.github/workflows/deploy.yml`

**예상 시간**: 1-2시간

---

### 8. 데이터 검증 함수 (선택)

**목표**: 데이터 수집 실패 시 알림

**작업 내용**:
- [ ] `functions/data_validation_function/` 생성
  - BigQuery 데이터 검증
  - Alert Policy 연동
  
**참고 파일**:
- `naver/functions/data_validation_function/`

**예상 시간**: 1-2시간

---

### 9. 문서화 (권장)

**작업 내용**:
- [ ] `README.md` 업데이트
- [ ] `docs/ONBOARDING.md` 작성
- [ ] API 문서 업데이트
- [ ] 배포 가이드 작성

**예상 시간**: 1-2시간

---

## 📊 진행 상황 요약

### 완료 (✅)
- 로컬 파이프라인 구현
- API 분석 및 데이터 구조 파악
- 정렬 옵션별 수집 기능

### 다음 우선순위 (🎯)
1. **GCS/BigQuery 연동** (가장 중요)
2. **Cloud Functions 배포 구조**
3. **로컬 테스트**
4. **GCP 인프라 설정**
5. **실제 배포 및 테스트**

---

## 💡 권장 진행 순서

1. **먼저**: GCS/BigQuery 연동 모듈 구현
   - 로컬에서 테스트 가능
   - 실제 데이터 저장 확인 가능

2. **그 다음**: Cloud Functions 구조 생성
   - 로컬 Functions Framework로 테스트
   - 실제 배포 전 검증

3. **마지막**: GCP 인프라 설정 및 배포
   - 모든 코드가 준비된 후 배포
   - 한 번에 완성도 높게 배포

---

## 🔍 참고할 네이버 프로젝트 파일들

### 핵심 모듈
- `naver/src/upload_gcs.py` - GCS 업로드 로직
- `naver/src/upload_bigquery.py` - BigQuery 업로드 로직
- `naver/functions/pipeline_function/main.py` - Cloud Functions 진입점

### 배포 스크립트
- `naver/functions/pipeline_function/deploy.sh` - 배포 스크립트
- `naver/scripts/setup/setup_scheduler.sh` - Scheduler 설정

### 문서
- `naver/docs/planning/03_GCP_배포_계획.md` - 배포 계획
- `naver/README.md` - 프로젝트 개요

---

**마지막 업데이트**: 2026-01-01

