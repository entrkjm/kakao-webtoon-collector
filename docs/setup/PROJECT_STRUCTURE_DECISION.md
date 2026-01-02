# GCP 프로젝트 구조 결정 문서

## 📋 현재 상황

### 네이버 웹툰 수집기
- **GCP 프로젝트 ID**: `naver-webtoon-collector`
- **독립 프로젝트**: ✅ 예
- **서비스 계정**: `webtoon-collector@naver-webtoon-collector.iam.gserviceaccount.com`
- **GCS 버킷**: `naver-webtoon-raw`
- **BigQuery 데이터셋**: `naver_webtoon`

### 카카오 웹툰 수집기 (현재)
- **GCP 프로젝트 ID**: `kakao-webtoon-collector` (기본값, 아직 생성 안 됨)
- **독립 프로젝트**: ⏳ 결정 필요
- **서비스 계정**: `webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com` (예상)
- **GCS 버킷**: `kakao-webtoon-raw` (예상)
- **BigQuery 데이터셋**: `kakao_webtoon` (예상)

---

## 🤔 독립 프로젝트 vs 통합 프로젝트

### 옵션 1: 독립 프로젝트 (권장) ✅

**구조**:
- 네이버: `naver-webtoon-collector`
- 카카오: `kakao-webtoon-collector`

**장점**:
1. **Always Free 티어를 각각 사용 가능** ⭐ 가장 큰 장점
   - GCS: 각 프로젝트마다 5GB 무료 (총 10GB)
   - BigQuery: 각 프로젝트마다 10GB 무료 (총 20GB)
   - Cloud Functions: 각 프로젝트마다 200만 요청/월 무료 (총 400만)
   - Cloud Scheduler: 각 프로젝트마다 3개 작업 무료 (총 6개)

2. **비용 관리 분리**
   - 각 프로젝트별로 비용 추적 가능
   - 프로젝트별 예산 설정 가능

3. **권한 관리 분리**
   - 각 프로젝트별로 독립적인 IAM 설정
   - 보안 격리

4. **프로젝트 간 영향 없음**
   - 한 프로젝트의 문제가 다른 프로젝트에 영향 없음
   - 독립적인 배포 및 관리

5. **확장성**
   - 향후 다른 플랫폼 추가 시에도 동일한 패턴 적용 가능

**단점**:
1. 프로젝트 관리가 복잡해질 수 있음
   - 여러 프로젝트 전환 필요
   - 하지만 스크립트로 자동화 가능

2. 공통 리소스 공유 어려움
   - 하지만 현재는 공통 리소스가 없음

---

### 옵션 2: 통합 프로젝트

**구조**:
- 단일 프로젝트: `webtoon-collectors` (예상)
- 네이버와 카카오가 같은 프로젝트 내에서 리소스 분리

**장점**:
1. 단일 프로젝트 관리
   - 프로젝트 전환 불필요

**단점**:
1. **Always Free 티어를 한 번만 사용** ⚠️ 큰 단점
   - GCS: 5GB만 무료 (두 프로젝트가 공유)
   - BigQuery: 10GB만 무료
   - Cloud Functions: 200만 요청/월만 무료

2. 비용 관리 복잡
   - 프로젝트 내에서 리소스별로 비용 추적 필요

3. 권한 관리 복잡
   - 같은 프로젝트 내에서 리소스별 권한 설정 필요

---

## ✅ 결정: 독립 프로젝트 사용

**결정 이유**:
1. **Always Free 티어를 각각 사용할 수 있어서 비용 효율적**
   - 네이버와 카카오가 각각 무료 할당량 사용 가능
   - 총 무료 할당량이 2배

2. **네이버 프로젝트와 일관성 유지**
   - 이미 네이버는 독립 프로젝트로 구성됨
   - 동일한 패턴 유지

3. **확장성**
   - 향후 다른 플랫폼 추가 시에도 동일한 패턴 적용 가능

4. **관리 복잡도는 스크립트로 해결 가능**
   - 프로젝트 전환 스크립트 작성 가능
   - 자동화로 관리 부담 최소화

---

## 📝 구현 계획

### 1. 카카오 GCP 프로젝트 생성
```bash
# 프로젝트 생성
gcloud projects create kakao-webtoon-collector \
  --name="카카오 웹툰 수집기" \
  --set-as-default

# 프로젝트 ID 확인
gcloud config get-value project
```

### 2. 카카오 프로젝트 설정
- 모든 스크립트와 코드에서 `kakao-webtoon-collector` 프로젝트 ID 사용
- 네이버와 동일한 구조로 설정

### 3. 프로젝트 전환 스크립트 (선택사항)
```bash
# 네이버 프로젝트로 전환
./scripts/utils/switch_to_naver.sh

# 카카오 프로젝트로 전환
./scripts/utils/switch_to_kakao.sh
```

---

## 🔧 현재 코드 상태

### 카카오 프로젝트 기본값 설정 확인

**현재 설정된 기본값**:
- `src/upload_gcs.py`: `GCS_PROJECT_ID = 'kakao-webtoon-collector'`
- `src/upload_bigquery.py`: `BIGQUERY_PROJECT_ID = 'kakao-webtoon-collector'`
- `functions/pipeline_function/main.py`: `BIGQUERY_PROJECT_ID = 'kakao-webtoon-collector'`
- `scripts/setup/setup_bigquery.sql`: `kakao-webtoon-collector`
- `scripts/setup/setup_gcp_prerequisites.sh`: 프로젝트 ID는 `gcloud config`에서 가져옴

**결론**: 이미 독립 프로젝트 구조로 설계되어 있음 ✅

---

## 📊 비교표

| 항목 | 독립 프로젝트 | 통합 프로젝트 |
|------|--------------|--------------|
| Always Free 티어 | 각 프로젝트마다 (2배) | 한 번만 |
| GCS 무료 용량 | 10GB (5GB × 2) | 5GB |
| BigQuery 무료 용량 | 20GB (10GB × 2) | 10GB |
| Cloud Functions 무료 요청 | 400만/월 (200만 × 2) | 200만/월 |
| 비용 관리 | 프로젝트별 분리 | 통합 관리 |
| 권한 관리 | 프로젝트별 분리 | 통합 관리 |
| 관리 복잡도 | 중간 (스크립트로 해결) | 낮음 |
| 확장성 | 높음 | 낮음 |

---

## ✅ 최종 결정

**독립 프로젝트 사용** (`kakao-webtoon-collector`)

**이유**:
1. Always Free 티어를 각각 사용 가능 (비용 효율적)
2. 네이버 프로젝트와 일관성 유지
3. 확장성 고려
4. 이미 코드가 독립 프로젝트 구조로 설계되어 있음

---

**작성일**: 2026-01-01  
**작성자**: AI Assistant  
**검토 필요**: 사용자 확인

