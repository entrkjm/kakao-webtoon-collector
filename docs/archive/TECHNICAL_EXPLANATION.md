# 카카오 웹툰 API 발견 과정 - 기술적 상세 설명

## 1. Performance 로그 (Chrome DevTools Protocol)

### 정의
Chrome DevTools Protocol의 Performance 로그는 브라우저의 성능 이벤트를 기록하는 메커니즘입니다.

### 작동 방식
```python
# Selenium에서 Performance 로그 활성화
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

# 로그 수집
logs = driver.get_log('performance')
```

### 로그 구조
각 로그 엔트리는 다음과 같은 구조를 가집니다:
```json
{
  "level": "INFO",
  "message": "{\"message\":{\"method\":\"Network.responseReceived\",\"params\":{...}}}",
  "timestamp": 1234567890
}
```

### 주요 이벤트 타입
1. **Network.requestWillBeSent**: HTTP 요청이 전송되기 직전
2. **Network.responseReceived**: HTTP 응답을 받았을 때
3. **Network.loadingFinished**: 리소스 로딩 완료

### 한계점
- **문제**: 모든 네트워크 요청이 Performance 로그에 기록되지는 않음
- **원인**: 
  - CORS preflight 요청은 기록되지 않을 수 있음
  - Service Worker를 통한 요청은 기록되지 않을 수 있음
  - 일부 XHR/Fetch 요청이 타이밍 문제로 누락될 수 있음
  - 브라우저 내부 요청은 기록되지 않음

### 실제 코드에서의 문제
```python
# Performance 로그로는 이 요청을 캡처하지 못함
# JavaScript에서 fetch()로 호출한 요청이 로그에 나타나지 않음
fetch('https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon')
```

---

## 2. JavaScript 인터셉터 (Function Hooking)

### 정의
JavaScript의 함수를 원본 함수로 대체하여 호출을 가로채는 기법입니다.

### 작동 원리
```javascript
// 원본 함수 저장
const originalFetch = window.fetch;

// 함수 재정의 (Hooking)
window.fetch = function(...args) {
    // 호출 전처리
    const url = args[0];
    const options = args[1] || {};
    
    // 로깅 또는 수정
    console.log('Fetch 호출:', url);
    window._apiCalls.push({
        type: 'fetch',
        url: url,
        method: options.method || 'GET'
    });
    
    // 원본 함수 호출
    return originalFetch.apply(this, args);
};
```

### 왜 필요한가?
1. **Performance 로그의 한계 보완**: 
   - Performance 로그는 브라우저 엔진 레벨에서 작동
   - JavaScript 인터셉터는 JavaScript 실행 컨텍스트 레벨에서 작동
   - 모든 fetch/XHR 호출을 100% 캡처 가능

2. **타이밍 문제 해결**:
   - Performance 로그는 비동기적으로 수집됨
   - 인터셉터는 함수 호출 시점에 즉시 실행됨

### XMLHttpRequest 후킹
```javascript
// XMLHttpRequest.prototype.open을 후킹
const originalOpen = XMLHttpRequest.prototype.open;

XMLHttpRequest.prototype.open = function(method, url, ...args) {
    // 호출 캡처
    window._apiCalls.push({
        type: 'xhr',
        url: url,
        method: method
    });
    
    // 원본 함수 호출
    return originalOpen.apply(this, [method, url, ...args]);
};
```

### Selenium에서의 사용
```python
# JavaScript 실행 컨텍스트에서 인터셉터 설치
interceptor_script = """
(function() {
    const originalFetch = window.fetch;
    window._apiCalls = [];
    
    window.fetch = function(...args) {
        window._apiCalls.push({
            type: 'fetch',
            url: args[0],
            method: args[1]?.method || 'GET'
        });
        return originalFetch.apply(this, args);
    };
})();
"""

driver.execute_script(interceptor_script)

# 나중에 캡처한 호출 가져오기
api_calls = driver.execute_script("return window._apiCalls || [];")
```

---

## 3. XHR vs Fetch

### XMLHttpRequest (XHR)
- **정의**: 브라우저에서 HTTP 요청을 보내는 전통적인 API
- **특징**: 
  - 콜백 기반 (이벤트 리스너)
  - 모든 브라우저에서 지원
  - 레거시 코드에서 주로 사용

```javascript
const xhr = new XMLHttpRequest();
xhr.open('GET', 'https://api.example.com/data');
xhr.onload = function() {
    console.log(xhr.responseText);
};
xhr.send();
```

### Fetch API
- **정의**: Promise 기반의 현대적인 HTTP 요청 API
- **특징**:
  - Promise 기반 (async/await 지원)
  - ES6+ 표준
  - 최신 프레임워크에서 주로 사용

```javascript
fetch('https://api.example.com/data')
    .then(response => response.json())
    .then(data => console.log(data));
```

### 왜 둘 다 인터셉트해야 하는가?
- **레거시 코드**: 일부 라이브러리는 여전히 XHR 사용
- **최신 코드**: React, Next.js 등은 주로 Fetch 사용
- **완전한 커버리지**: 둘 다 후킹해야 모든 요청을 캡처 가능

---

## 4. 네트워크 요청 모니터링의 계층 구조

### 계층 1: 브라우저 엔진 레벨 (Performance 로그)
```
HTTP 요청 → 브라우저 엔진 → Performance 로그
```
- **장점**: 모든 HTTP 요청을 이론적으로 캡처 가능
- **단점**: 
  - 일부 요청이 누락될 수 있음
  - 타이밍 문제
  - 브라우저 구현에 의존

### 계층 2: JavaScript 실행 컨텍스트 레벨 (인터셉터)
```
JavaScript 코드 → fetch/XHR 호출 → 인터셉터 → 실제 네트워크 요청
```
- **장점**: 
  - 100% 캡처 보장 (JavaScript에서 호출한 모든 요청)
  - 즉시 실행 (타이밍 문제 없음)
- **단점**: 
  - JavaScript로 호출하지 않은 요청은 캡처 불가
  - (예: HTML의 `<img src="...">`, `<link href="...">` 등)

### 계층 3: 네트워크 레벨 (프록시, 패킷 캡처)
```
애플리케이션 → 네트워크 스택 → 실제 네트워크
```
- **도구**: Charles Proxy, mitmproxy, Wireshark
- **장점**: 모든 네트워크 트래픽 캡처
- **단점**: 설정 복잡, HTTPS 인증서 설치 필요

---

## 5. SSR (Server Side Rendering)과 API의 관계

### SSR의 작동 방식

#### 전통적인 SSR (예: PHP, JSP)
```
1. 사용자 요청 → 서버
2. 서버에서 데이터베이스 조회
3. 서버에서 HTML 생성
4. 완성된 HTML을 클라이언트에 전송
5. 클라이언트는 HTML만 렌더링
```

#### Next.js의 SSR
```
1. 사용자 요청 → Next.js 서버
2. 서버에서 getServerSideProps() 실행
3. getServerSideProps() 내부에서 API 호출 (서버 → API 서버)
4. 서버에서 React 컴포넌트 렌더링 (데이터 포함)
5. HTML + __NEXT_DATA__ (JSON) 전송
6. 클라이언트는 HTML 렌더링 + __NEXT_DATA__로 하이드레이션
```

### __NEXT_DATA__ 스크립트 태그

#### 정의
Next.js가 서버에서 렌더링한 초기 데이터를 클라이언트에 전달하기 위한 JSON 스크립트 태그입니다.

#### 구조
```html
<script id="__NEXT_DATA__" type="application/json">
{
  "props": {
    "pageProps": {
      "initialData": {
        "webtoons": [...]
      }
    }
  },
  "query": {},
  "buildId": "..."
}
</script>
```

#### 목적
1. **하이드레이션 (Hydration)**: 
   - 서버에서 렌더링한 HTML과 클라이언트 React 컴포넌트를 연결
   - 클라이언트에서 React가 이 데이터를 사용하여 컴포넌트 상태 초기화

2. **초기 데이터 전달**:
   - 서버에서 가져온 데이터를 클라이언트에 전달
   - 클라이언트에서 추가 API 호출 없이 초기 렌더링 가능

### 클라이언트 사이드 API 호출

#### 시나리오 1: 초기 로드는 SSR, 상호작용은 클라이언트 API
```
초기 로드:
  사용자 → Next.js 서버 → API 서버 → HTML 생성 → 클라이언트

요일 변경 (클라이언트 상호작용):
  JavaScript → fetch('https://gateway-kw.kakao.com/...') → API 서버
```

#### 시나리오 2: 모든 것이 클라이언트 API
```
초기 로드:
  사용자 → Next.js 서버 → HTML (빈 상태) → 클라이언트
  클라이언트 JavaScript → fetch('https://gateway-kw.kakao.com/...') → API 서버

요일 변경:
  JavaScript → fetch('https://gateway-kw.kakao.com/...') → API 서버
```

### 카카오 웹툰의 경우

#### 관찰된 사실
1. **__NEXT_DATA__ 존재**: HTML에 초기 데이터 포함
2. **클라이언트 API 호출**: 요일/필터 변경 시 추가 API 호출 발생

#### 결론
- **하이브리드 방식**: 초기 로드는 SSR, 상호작용은 클라이언트 API
- **API 엔드포인트**: `https://gateway-kw.kakao.com/section/v2/timetables/days`
- **이유**: 
  - 초기 로드는 빠른 SSR로 SEO와 초기 로딩 속도 확보
  - 상호작용은 클라이언트 API로 동적 업데이트

---

## 6. 왜 Performance 로그로는 찾지 못했는가?

### 기술적 원인

#### 1. 이벤트 타임라인 문제
```
시간축:
T0: 버튼 클릭
T1: JavaScript 이벤트 핸들러 실행
T2: fetch() 호출
T3: 네트워크 요청 전송
T4: Performance 로그에 기록
T5: 우리가 로그를 읽음

문제: T4와 T5 사이의 타이밍 문제
- 로그 버퍼가 비워지기 전에 읽으면 누락
- 비동기 로그 수집으로 인한 지연
```

#### 2. 로그 필터링 문제
```python
# 초기 필터링 로직
if any(keyword in url for keyword in ['api', 'webtoon', 'chart']):
    # 이 필터를 통과하지 못함
    # 'gateway-kw.kakao.com/section/v2/timetables/days'
    # 'section'과 'timetables'는 키워드에 없음
```

#### 3. 도메인 필터링 오류
```python
# 잘못된 필터링
exclude_domains = ['kakaopagecdn.com']  # CDN 제외

# 문제: 'gateway-kw.kakao.com'도 제외될 수 있음
# 'kakao'가 포함되어 있어서 제외 로직에 걸릴 수 있음
```

### 인터셉터가 성공한 이유

#### 1. 동기적 실행
```javascript
// 인터셉터는 함수 호출 시점에 즉시 실행
window.fetch = function(...args) {
    // 이 코드는 fetch() 호출과 동시에 실행됨
    window._apiCalls.push({...});
    return originalFetch.apply(this, args);
};
```

#### 2. 100% 캡처 보장
- JavaScript에서 호출한 모든 fetch/XHR 요청을 캡처
- Performance 로그의 비동기 특성과 무관

#### 3. 필터링 불필요
- 모든 호출을 캡처한 후 나중에 필터링
- Performance 로그는 미리 필터링해야 함

---

## 7. 발견한 API의 구조

### 엔드포인트
```
https://gateway-kw.kakao.com/section/v2/timetables/days
```

### 쿼리 파라미터
```
?placement=timetable_{weekday}[_{filter}]
```

### Placement 패턴
- `timetable_mon`: 월요일 전체
- `timetable_mon_free_publishing`: 월요일 연재무료
- `timetable_wed`: 수요일 전체
- `timetable_wed_free_publishing`: 수요일 연재무료

### HTTP 메서드
- **GET**: 데이터 조회

### 인증
- **현재**: 인증 불필요 (공개 API)
- **헤더**: User-Agent, Referer, Origin 권장

### 응답 구조
```json
{
  "data": [
    {
      "id": "...",
      "title": "월",
      "module": "WEEKDAYS",
      "placement": "timetable_mon",
      "cardGroups": [
        {
          "cards": [
            {
              "id": "...",
              "content": {
                "title": "웹툰 제목",
                "author": "작가명",
                ...
              }
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 8. 요약: 기술적 핵심

### Performance 로그의 한계
- **비동기 로그 수집**: 요청 발생과 로그 기록 사이의 지연
- **브라우저 구현 의존**: 모든 요청이 기록되리라는 보장 없음
- **타이밍 문제**: 로그 버퍼를 읽는 시점에 따라 누락 가능

### JavaScript 인터셉터의 장점
- **동기적 실행**: 함수 호출 시점에 즉시 실행
- **100% 캡처**: JavaScript에서 호출한 모든 요청 보장
- **타이밍 문제 없음**: 요청 발생과 동시에 캡처

### 발견 과정
1. **Performance 로그 시도**: 실패 (추적 API만 발견)
2. **JavaScript 인터셉터 추가**: 성공 (실제 API 발견)
3. **API 테스트**: 성공 (모든 요일/필터 조합 작동 확인)

### 결론
- **API 존재**: `gateway-kw.kakao.com/section/v2/timetables/days`
- **발견 방법**: JavaScript 인터셉터가 핵심
- **이유**: Performance 로그의 비동기 특성과 타이밍 문제를 인터셉터가 해결

