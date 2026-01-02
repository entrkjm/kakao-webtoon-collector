# 카카오 웹툰 페이지 분석 가이드

## AI 어시스턴트가 웹페이지를 분석하는 방법

### 1. 직접 브라우저 열기
**불가능**: AI 어시스턴트는 직접 브라우저를 열 수 없습니다.

**대안**: Python 스크립트를 작성하여 Selenium으로 브라우저를 자동화합니다.

### 2. 웹페이지 구조 파악
**가능**: requests나 Selenium으로 HTML을 가져와 BeautifulSoup으로 분석합니다.

### 3. JavaScript 이벤트 발생 및 데이터 수집
**가능**: Selenium으로 JavaScript를 실행하고 네트워크 요청을 모니터링합니다.

## 제공된 분석 스크립트

### 1. `scripts/analyze_page.py`
기본 페이지 구조 분석 스크립트

**기능**:
- requests로 HTML 수집 및 분석
- Selenium으로 JavaScript 실행 후 분석 (선택적)
- API 엔드포인트 후보 찾기
- 웹툰 링크 찾기

**실행 방법**:
```bash
cd kakao
python scripts/analyze_page.py
```

### 2. `scripts/find_api_endpoints.py`
API 엔드포인트 찾기 스크립트 (Selenium 필요)

**기능**:
- Selenium으로 브라우저 열기
- 네트워크 요청 모니터링
- API 엔드포인트 자동 발견
- 발견된 API 테스트

**실행 방법**:
```bash
# Selenium 설치
pip install selenium

# ChromeDriver 설치 (macOS)
brew install chromedriver

# 또는 수동 설치
# https://chromedriver.chromium.org/downloads

# 스크립트 실행
python scripts/find_api_endpoints.py
```

## 분석 결과 확인

분석 결과는 `data/analysis/` 디렉토리에 저장됩니다:

- `analysis_requests_*.json`: requests 분석 결과
- `analysis_selenium_*.json`: Selenium 분석 결과
- `sample_*.html`: HTML 샘플
- `api_endpoints_*.json`: 발견된 API 엔드포인트
- `api_test_results_*.json`: API 테스트 결과

## 다음 단계

1. **분석 스크립트 실행**: 실제 카카오 웹툰 페이지 구조 파악
2. **API 엔드포인트 찾기**: 네트워크 요청 모니터링으로 실제 API 확인
3. **파싱 로직 구현**: 발견된 구조에 맞게 `extract.py`, `parse.py` 수정
4. **테스트**: 로컬에서 실제 데이터 수집 테스트

## 참고

- 네이버 웹툰 수집기는 브라우저 개발자 도구의 네트워크 탭을 분석하여 API 엔드포인트를 찾았습니다.
- 카카오 웹툰도 유사한 방법으로 API를 찾을 수 있을 것입니다.
- Selenium 없이도 requests만으로도 기본 구조는 파악할 수 있지만, JavaScript로 동적 렌더링되는 경우 Selenium이 필요합니다.

