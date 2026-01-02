# GitHub Actions CI/CD 설정 가이드

> **목적**: GitHub에 코드를 푸시하면 자동으로 Cloud Functions를 배포하도록 설정

---

## 📋 사전 준비

### 1. GCP 서비스 계정 키 생성

GitHub Actions에서 GCP에 인증하기 위해 서비스 계정 키가 필요합니다.

```bash
# 서비스 계정 키 생성
gcloud iam service-accounts keys create ~/gcp-sa-key.json \
    --iam-account=webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com

# 키 파일 내용 확인 (GitHub Secrets에 등록할 때 사용)
cat ~/gcp-sa-key.json
```

**주의**: 키 파일은 안전하게 보관하고, GitHub Secrets에 등록한 후 로컬 파일은 삭제하세요.

---

## 🔐 GitHub Secrets 설정

GitHub 저장소에 다음 Secrets를 등록해야 합니다:

### 1. GitHub 저장소 설정 페이지 접속

1. GitHub 저장소 페이지 접속
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 클릭

### 2. 필요한 Secrets

#### `GCP_SA_KEY` (필수)
- **이름**: `GCP_SA_KEY`
- **값**: 서비스 계정 키 JSON 파일의 전체 내용
- **설명**: GCP 인증용 서비스 계정 키

**등록 방법**:
```bash
# 키 파일 내용을 복사
cat ~/gcp-sa-key.json | pbcopy  # macOS
# 또는
cat ~/gcp-sa-key.json | xclip -selection clipboard  # Linux
```

GitHub Secrets에 붙여넣기

#### `NOTIFICATION_CHANNEL_EMAIL` (선택사항)
- **이름**: `NOTIFICATION_CHANNEL_EMAIL`
- **값**: 이메일 주소 (쉼표로 구분 가능)
- **설명**: 데이터 검증 함수 알림 이메일 주소

---

## 📝 워크플로우 파일

워크플로우 파일은 `.github/workflows/deploy.yml`에 있습니다.

### 트리거 조건

- **자동 실행**: `main` 브랜치에 push 시 다음 파일이 변경되면 실행
  - `functions/**`
  - `src/**`
  - `.github/workflows/deploy.yml`
- **수동 실행**: GitHub Actions 페이지에서 `workflow_dispatch`로 수동 실행 가능

### 배포 대상

1. **pipeline-function**: 메인 데이터 수집 파이프라인
2. **data-validation-function**: 데이터 검증 함수

---

## 🚀 사용 방법

### 자동 배포

1. 코드 수정 후 `main` 브랜치에 push
2. GitHub Actions가 자동으로 실행
3. Actions 탭에서 배포 상태 확인

### 수동 배포

1. GitHub 저장소 → **Actions** 탭
2. **Deploy Cloud Functions** 워크플로우 선택
3. **Run workflow** 클릭
4. 브랜치 선택 후 **Run workflow** 클릭

---

## ✅ 배포 확인

### GitHub Actions에서 확인

1. **Actions** 탭에서 워크플로우 실행 상태 확인
2. 각 job의 로그 확인
3. 배포 성공 여부 확인

### GCP에서 확인

```bash
# Cloud Functions 목록 확인
gcloud functions list --gen2 --region=asia-northeast3 --project=kakao-webtoon-collector

# 특정 함수 확인
gcloud functions describe pipeline-function \
    --gen2 \
    --region=asia-northeast3 \
    --project=kakao-webtoon-collector
```

---

## 🔧 문제 해결

### 인증 오류

**증상**: `Permission denied` 또는 `Authentication failed`

**해결 방법**:
1. `GCP_SA_KEY` Secret이 올바르게 설정되었는지 확인
2. 서비스 계정에 필요한 권한이 있는지 확인:
   ```bash
   gcloud projects get-iam-policy kakao-webtoon-collector \
       --flatten="bindings[].members" \
       --filter="bindings.members:webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com"
   ```

### 배포 실패

**증상**: Cloud Functions 배포 실패

**해결 방법**:
1. GitHub Actions 로그 확인
2. 로컬에서 수동 배포 테스트:
   ```bash
   cd functions/pipeline_function
   ./deploy.sh
   ```
3. 환경 변수 확인

### src 디렉토리 복사 실패

**증상**: `src 디렉토리 준비 실패`

**해결 방법**:
- 워크플로우에서 `src` 디렉토리를 자동으로 복사하도록 설정되어 있음
- 만약 문제가 발생하면 `.github/workflows/deploy.yml`의 `Prepare pipeline function` 단계 확인

---

## 📚 관련 문서

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Google Cloud GitHub Actions](https://github.com/google-github-actions/setup-gcloud)
- [Cloud Functions 배포 가이드](../functions/pipeline_function/README.md)

---

## 💡 팁

- **보안**: 서비스 계정 키는 절대 코드에 커밋하지 마세요
- **테스트**: 먼저 수동 실행으로 테스트한 후 자동 배포 활성화
- **롤백**: 배포 실패 시 이전 버전으로 수동 롤백 가능
- **비용**: GitHub Actions는 무료 플랜에서도 충분한 시간 제공 (월 2,000분)

---

**마지막 업데이트**: 2026-01-01

