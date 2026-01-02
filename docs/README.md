# 카카오 웹툰 수집기 문서

> 카카오 웹툰 주간 차트 데이터 수집 파이프라인 문서

---

## 📚 문서 구조

### 📁 [setup/](./setup/)
설정 및 배포 가이드

- **GCP_SETUP_GUIDE.md** - GCP 인프라 설정 가이드
- **DEPLOYMENT_CHECKLIST.md** - 배포 체크리스트
- **BILLING_SETUP.md** - 결제 계정 연결 가이드
- **PROJECT_STRUCTURE_DECISION.md** - 프로젝트 구조 결정 사항
- **alert_setup_guide.md** - Alert Policy 설정 가이드
- **alert_test_guide.md** - Alert Policy 테스트 가이드

### 📁 [reference/](./reference/)
참고 문서

- **API_DISCOVERY_RESULT.md** - API 발견 결과 및 엔드포인트 정보
- **API_DISCOVERY_STRATEGY.md** - API 발견 전략
- **WHY_API_NOT_FOUND_INITIALLY.md** - 초기 API 발견 실패 원인 분석
- **SCHEMA_COMPARISON.md** - 네이버/카카오 스키마 비교

### 📁 [troubleshooting/](./troubleshooting/)
문제 해결 가이드

- **CHART_DATE_ISSUE.md** - chart_date 파라미터 문제 분석

### 📁 [archive/](./archive/)
과거/중복 문서 (참고용)

- 설명 문서 (SIMPLE_EXPLANATION.md, STEP_BY_STEP.md 등)
- 이전 다음 단계 문서 (NEXT_STEPS_*.md)

---

## 🚀 빠른 시작

### 처음 시작하는 경우

1. [GCP_SETUP_GUIDE.md](./setup/GCP_SETUP_GUIDE.md) - GCP 인프라 설정
2. [DEPLOYMENT_CHECKLIST.md](./setup/DEPLOYMENT_CHECKLIST.md) - 배포 체크리스트
3. [alert_setup_guide.md](./setup/alert_setup_guide.md) - Alert Policy 설정

### API 정보가 필요한 경우

- [API_DISCOVERY_RESULT.md](./reference/API_DISCOVERY_RESULT.md) - API 엔드포인트 및 사용법

### 문제 해결이 필요한 경우

- [troubleshooting/](./troubleshooting/) - 문제별 해결 가이드

---

## 📝 주요 문서

### 설정 가이드
- [GCP 인프라 설정](./setup/GCP_SETUP_GUIDE.md)
- [Alert Policy 설정](./setup/alert_setup_guide.md)

### 참고 문서
- [API 엔드포인트](./reference/API_DISCOVERY_RESULT.md)
- [스키마 비교](./reference/SCHEMA_COMPARISON.md)

### 문제 해결
- [chart_date 문제](./troubleshooting/CHART_DATE_ISSUE.md)

---

**마지막 업데이트**: 2026-01-01

