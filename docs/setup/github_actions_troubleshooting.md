# GitHub Actions 인증 오류 해결 가이드

> **오류**: `google-github-actions/auth failed with: the GitHub Action workflow must specify exactly one of "workload_identity_provider" or "credentials_json"!`

---

## 🔍 오류 원인

이 오류는 `credentials_json`이 제대로 전달되지 않았을 때 발생합니다.

**가능한 원인**:
1. GitHub Secret이 비어있거나 잘못된 형식
2. Secret 이름이 정확하지 않음 (대소문자, 언더스코어)
3. Secret 값이 JSON 형식이 아님

---

## ✅ 해결 방법

### 방법 1: GitHub Secrets 재확인 및 재등록

#### 1단계: Secret 확인

1. GitHub 저장소 접속: https://github.com/entrkjm/kakao-webtoon-collector
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **GCP_SA_KEY** Secret 확인
   - 존재하는지 확인
   - 값이 올바른 JSON 형식인지 확인

#### 2단계: Secret 재등록 (필요시)

**기존 Secret 삭제**:
1. **GCP_SA_KEY** Secret 옆의 **"..."** 메뉴 클릭
2. **"Delete"** 클릭

**새 Secret 등록**:

1. **서비스 계정 키 재생성**:
```bash
gcloud iam service-accounts keys create ~/gcp-sa-key.json \
    --iam-account=webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com \
    --project=kakao-webtoon-collector
```

2. **키 파일 내용 복사**:
```bash
# macOS
cat ~/gcp-sa-key.json | pbcopy

# Linux
cat ~/gcp-sa-key.json | xclip -selection clipboard
```

3. **GitHub Secrets에 등록**:
   - **"New repository secret"** 클릭
   - **Name**: `GCP_SA_KEY` (정확히 이 이름)
   - **Secret**: (Cmd+V로 붙여넣기)
   - **"Add secret"** 클릭

4. **키 파일 삭제** (보안):
```bash
rm ~/gcp-sa-key.json
```

---

### 방법 2: 워크플로우 파일 확인

워크플로우 파일이 올바른 형식인지 확인:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}
```

**확인 사항**:
- `credentials_json:` (콜론 포함)
- `${{ secrets.GCP_SA_KEY }}` (정확한 이름, 대소문자 구분)
- 들여쓰기가 올바른지 확인 (2칸 또는 4칸 일관성)

---

### 방법 3: Secret 값 형식 확인

Secret 값은 **유효한 JSON 형식**이어야 합니다:

```json
{
  "type": "service_account",
  "project_id": "kakao-webtoon-collector",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "webtoon-collector@kakao-webtoon-collector.iam.gserviceaccount.com",
  ...
}
```

**주의사항**:
- 전체 JSON 내용이 복사되어야 함
- 줄바꿈 문자(`\n`)가 포함되어야 함
- 따옴표가 올바르게 이스케이프되어야 함

---

## 🔧 문제 해결 체크리스트

- [ ] GitHub Secrets에 `GCP_SA_KEY`가 존재하는가?
- [ ] Secret 이름이 정확히 `GCP_SA_KEY`인가? (대소문자 확인)
- [ ] Secret 값이 유효한 JSON 형식인가?
- [ ] 워크플로우 파일의 `credentials_json: ${{ secrets.GCP_SA_KEY }}` 형식이 올바른가?
- [ ] Secret을 재등록했는가?

---

## 📚 참고

- [네이버 프로젝트 워크플로우](../naver/.github/workflows/deploy.yml)
- [GitHub Actions 인증 문서](https://github.com/google-github-actions/auth)

---

**마지막 업데이트**: 2026-01-01

