# 카카오 웹툰 API 발견 - 기술적 상세 설명 (코드 중심)

## 1. Performance 로그의 작동 원리와 한계

### Chrome DevTools Protocol의 Performance 로그

#### 작동 방식
```python
# Selenium WebDriver에서 Performance 로그 활성화
chrome_options = Options()
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
driver = webdriver.Chrome(options=chrome_options)

# 로그 수집
logs = driver.get_log('performance')
```

#### 로그 엔트리 구조
```json
{
  "level": "INFO",
  "message": "{\"message\":{\"method\":\"Network.responseReceived\",\"params\":{\"response\":{\"url\":\"https://example.com/api\",\"status\":200}}}}",
  "timestamp": 1767190200937
}
```

#### 파싱 과정
```python
for log in logs:
    message = json.loads(log['message'])  # 문자열을 JSON으로 파싱
    method = message.get('message', {}).get('method', '')
    
    if method == 'Network.responseReceived':
        response = message.get('message', {}).get('params', {}).get('response', {})
        url = response.get('url', '')
        status = response.get('status', 0)
```

### 왜 API 요청을 놓쳤는가?

#### 문제 1: 비동기 로그 수집
```
실제 이벤트 타임라인:
T0: fetch('https://gateway-kw.kakao.com/...') 호출
T1: 네트워크 요청 전송 (TCP 연결 시작)
T2: HTTP 요청 전송
T3: HTTP 응답 수신
T4: Performance 로그에 이벤트 기록 (비동기)
T5: 우리가 driver.get_log('performance') 호출
T6: 로그 버퍼에서 읽기

문제: T4와 T5 사이의 타이밍
- T5가 T4보다 먼저 실행되면 요청을 놓침
- 로그 버퍼가 비워지면 이전 요청 기록 손실
```

#### 문제 2: 이벤트 누락 가능성
Chrome의 Performance 로그는 다음 경우에 이벤트를 기록하지 않을 수 있습니다:
1. **CORS preflight 요청**: OPTIONS 요청은 기록되지 않을 수 있음
2. **Service Worker**: Service Worker를 통한 요청은 별도 로그에 기록
3. **브라우저 내부 요청**: favicon, manifest.json 등은 기록되지 않을 수 있음
4. **빠른 요청**: 요청-응답이 너무 빠르면 로그에 기록되기 전에 완료될 수 있음

#### 실제 코드에서의 문제
```python
# 버튼 클릭
driver.execute_script("arguments[0].click();", button)
time.sleep(3)  # 3초 대기

# 로그 수집
logs = driver.get_log('performance')

# 문제: 3초 대기 중에 발생한 요청이 로그에 기록되지 않았을 수 있음
# 또는 로그 버퍼가 이미 비워졌을 수 있음
```

---

## 2. JavaScript 인터셉터 (Function Hooking)의 작동 원리

### 함수 후킹의 기본 개념

#### 원본 함수 저장
```javascript
// 원본 fetch 함수를 변수에 저장
const originalFetch = window.fetch;
// 이제 originalFetch는 원본 fetch 함수를 참조
```

#### 함수 재정의
```javascript
// window.fetch를 새로운 함수로 교체
window.fetch = function(...args) {
    // args[0]: URL (첫 번째 인자)
    // args[1]: options 객체 (두 번째 인자, 선택적)
    
    const url = args[0];
    const options = args[1] || {};
    const method = options.method || 'GET';
    
    // 호출 정보 저장
    window._apiCalls.push({
        type: 'fetch',
        url: url,
        method: method
    });
    
    // 원본 함수 호출 (실제 네트워크 요청 수행)
    return originalFetch.apply(this, args);
};
```

### apply() 메서드의 역할

#### 함수 호출 방식 비교
```javascript
// 일반 함수 호출
originalFetch(url, options);

// apply()를 사용한 호출
originalFetch.apply(this, args);
// this: 함수 내부에서 this로 참조할 객체
// args: 인자 배열
```

#### 왜 apply()를 사용하는가?
1. **인자 전달**: `args` 배열의 모든 요소를 개별 인자로 전달
2. **this 바인딩**: 원본 함수의 컨텍스트 유지
3. **동적 호출**: 인자 개수를 미리 알 수 없는 경우에 유용

### 즉시 실행 함수 (IIFE)로 네임스페이스 보호

```javascript
(function() {
    // 이 코드는 즉시 실행되며, 전역 스코프를 오염시키지 않음
    const originalFetch = window.fetch;
    window._apiCalls = [];
    
    window.fetch = function(...args) {
        window._apiCalls.push({...});
        return originalFetch.apply(this, args);
    };
})();
```

**이유:**
- 전역 변수 `originalFetch`를 생성하지 않음
- 다른 스크립트와의 충돌 방지
- 모듈화된 코드 구조

### XMLHttpRequest.prototype.open 후킹

#### 프로토타입 메서드 후킹
```javascript
// XMLHttpRequest의 프로토타입에 정의된 open 메서드를 후킹
const originalOpen = XMLHttpRequest.prototype.open;

XMLHttpRequest.prototype.open = function(method, url, ...args) {
    // method: 'GET', 'POST' 등
    // url: 요청 URL
    // args: 나머지 인자들 (async, user, password 등)
    
    window._apiCalls.push({
        type: 'xhr',
        url: url,
        method: method
    });
    
    // 원본 메서드 호출
    // this는 XMLHttpRequest 인스턴스
    return originalOpen.apply(this, [method, url, ...args]);
};
```

#### 왜 프로토타입을 수정하는가?
```javascript
// 모든 XMLHttpRequest 인스턴스가 이 메서드를 사용
const xhr1 = new XMLHttpRequest();
xhr1.open('GET', 'https://api1.com');  // 후킹된 메서드 호출

const xhr2 = new XMLHttpRequest();
xhr2.open('POST', 'https://api2.com');  // 후킹된 메서드 호출
```

---

## 3. Selenium에서 JavaScript 실행

### execute_script() 메서드

#### 기본 사용법
```python
# JavaScript 코드를 브라우저 컨텍스트에서 실행
result = driver.execute_script("return document.title;")
# result: 현재 페이지의 제목
```

#### 인터셉터 설치
```python
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

# 브라우저에서 실행 (페이지 로드 전에 실행해야 함)
driver.execute_script(interceptor_script)
```

#### 캡처한 데이터 가져오기
```python
# JavaScript 변수에서 데이터 가져오기
api_calls = driver.execute_script("return window._apiCalls || [];")
# api_calls: Python 리스트로 변환된 JavaScript 배열
```

### 실행 컨텍스트

#### JavaScript 실행 컨텍스트
```python
# 이 코드는 브라우저의 JavaScript 실행 컨텍스트에서 실행됨
driver.execute_script("window.myVariable = 'hello';")

# 브라우저의 전역 객체(window)에 접근 가능
value = driver.execute_script("return window.myVariable;")
# value: 'hello'
```

#### Python과 JavaScript 간 데이터 전달
```python
# Python → JavaScript
url = "https://example.com"
driver.execute_script(f"fetch('{url}');")

# JavaScript → Python
result = driver.execute_script("return {url: 'https://example.com', status: 200};")
# result: {'url': 'https://example.com', 'status': 200} (Python dict)
```

---

## 4. 왜 인터셉터가 성공했는가?

### 동기적 실행 vs 비동기 로그

#### Performance 로그 (비동기)
```
시간축:
T0: fetch('https://api.com') 호출
T1: 네트워크 요청 전송
T2: HTTP 응답 수신
T3: Performance 로그에 이벤트 추가 (비동기, 큐에 추가)
T4: 우리가 get_log() 호출
T5: 로그 버퍼 읽기

문제: T3과 T4의 순서가 보장되지 않음
- T4가 T3보다 먼저 실행되면 요청을 놓침
- 로그 버퍼가 비워지면 이전 요청 기록 손실
```

#### 인터셉터 (동기)
```
시간축:
T0: fetch('https://api.com') 호출
T1: 인터셉터 함수 실행 (즉시, 동기)
T2: window._apiCalls.push({...}) 실행 (즉시)
T3: originalFetch.apply() 호출 (네트워크 요청)
T4: 우리가 execute_script("return window._apiCalls") 호출
T5: 배열 반환

장점: T1과 T2는 fetch() 호출과 동시에 실행됨
- 타이밍 문제 없음
- 100% 캡처 보장
```

### 메모리 기반 저장

#### Performance 로그
- **저장 위치**: 브라우저 내부 로그 버퍼
- **접근 방식**: Selenium을 통한 비동기 읽기
- **문제**: 버퍼 크기 제한, 오래된 로그 손실

#### 인터셉터
- **저장 위치**: JavaScript 변수 (window._apiCalls)
- **접근 방식**: execute_script()로 직접 접근
- **장점**: 
  - 메모리에 직접 저장되어 즉시 접근 가능
  - 버퍼 크기 제한 없음 (브라우저 메모리 한도 내)
  - 명시적으로 관리 가능

---

## 5. 발견한 API의 기술적 세부사항

### RESTful API 구조

#### 엔드포인트 분석
```
https://gateway-kw.kakao.com/section/v2/timetables/days
```

**구조 분석:**
- `https://`: 프로토콜
- `gateway-kw.kakao.com`: 도메인 (게이트웨이 서버)
- `/section/v2/timetables/days`: 리소스 경로
  - `section`: 섹션 관련 API
  - `v2`: API 버전
  - `timetables`: 시간표 관련
  - `days`: 일별 데이터

#### 쿼리 파라미터
```
?placement=timetable_mon_free_publishing
```

**파라미터 구조:**
- `placement`: 리소스 배치/필터 파라미터
- 값 형식: `timetable_{weekday}[_{filter}]`
  - `weekday`: mon, tue, wed, thu, fri, sat, sun
  - `filter`: free_publishing, wait_free (선택적)

### HTTP 요청/응답

#### 요청 예시
```http
GET /section/v2/timetables/days?placement=timetable_mon HTTP/1.1
Host: gateway-kw.kakao.com
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...
Referer: https://webtoon.kakao.com/
Origin: https://webtoon.kakao.com
Accept: */*
```

#### 응답 예시
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 12345

{
  "data": [
    {
      "id": "...",
      "title": "월",
      "cardGroups": [...]
    }
  ]
}
```

### API 호출 패턴

#### Python에서의 호출
```python
import requests

url = "https://gateway-kw.kakao.com/section/v2/timetables/days"
params = {
    'placement': 'timetable_mon_free_publishing'
}

headers = {
    'User-Agent': 'Mozilla/5.0 ...',
    'Referer': 'https://webtoon.kakao.com/',
    'Origin': 'https://webtoon.kakao.com'
}

response = requests.get(url, params=params, headers=headers)
data = response.json()
```

#### JavaScript에서의 호출 (원본)
```javascript
// 카카오 웹툰 사이트에서 실제로 사용하는 코드 (추정)
fetch('https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon_free_publishing', {
    method: 'GET',
    headers: {
        'Referer': 'https://webtoon.kakao.com/',
        'Origin': 'https://webtoon.kakao.com'
    }
})
.then(response => response.json())
.then(data => {
    // 데이터 처리
});
```

---

## 6. 필터링 로직의 문제점

### 초기 필터링 로직

#### 문제가 있던 코드
```python
def is_api_candidate(url: str, mime_type: Optional[str]) -> bool:
    # API 키워드 포함 여부
    api_keywords = ['api', 'webtoon', 'chart', 'list', 'rank']
    
    if any(keyword in url.lower() for keyword in api_keywords):
        return True
    
    return False
```

#### 왜 실패했는가?
```python
# 실제 API URL
url = "https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon"

# 필터링 결과
'api' in url.lower()  # False
'webtoon' in url.lower()  # False
'chart' in url.lower()  # False
'list' in url.lower()  # False
'rank' in url.lower()  # False

# 결과: 필터링 실패, API로 인식되지 않음
```

### 개선된 필터링 로직

#### 수정된 코드
```python
def is_api_candidate(url: str, mime_type: Optional[str]) -> bool:
    if not url:
        return False
    
    url_lower = url.lower()
    
    # 제외할 도메인
    exclude_domains = [
        'google', 'facebook', 'googletagmanager',
        'kakaopagecdn.com',  # CDN은 제외
    ]
    
    for domain in exclude_domains:
        if domain in url_lower:
            return False
    
    # 카카오 도메인인 경우 더 관대하게
    if 'kakao' in url_lower or 'kakaopage' in url_lower:
        # gateway 도메인은 API로 인식
        if 'gateway' in url_lower:
            return True
        # JSON 응답인 경우
        if mime_type and 'json' in mime_type:
            return True
    
    # 일반적인 API 패턴
    api_keywords = ['api', 'webtoon', 'content', 'section', 'timetable']
    if any(keyword in url_lower for keyword in api_keywords):
        if mime_type and ('json' in mime_type or 'xml' in mime_type):
            return True
    
    return False
```

#### 개선점
1. **도메인 기반 필터링**: `gateway-kw.kakao.com` 명시적 포함
2. **MIME 타입 확인**: JSON 응답인 경우 포함
3. **키워드 확장**: `section`, `timetable` 추가

---

## 7. 전체 흐름 정리

### 첫 번째 시도 (실패)

```
1. Selenium으로 페이지 로드
2. Performance 로그 활성화
3. 버튼 클릭
4. time.sleep(5) 대기
5. driver.get_log('performance') 호출
6. 로그 파싱 및 필터링

결과: 추적 API만 발견 (Facebook, Google Analytics)
원인: 
- 실제 API 요청이 Performance 로그에 기록되지 않음
- 필터링 로직이 너무 엄격함
- 타이밍 문제
```

### 두 번째 시도 (성공)

```
1. Selenium으로 페이지 로드
2. Performance 로그 활성화
3. JavaScript 인터셉터 설치 (fetch/XHR 후킹)
4. 버튼 클릭
5. time.sleep(3) 대기
6. driver.execute_script("return window._apiCalls") 호출
7. 인터셉터로 캡처한 호출 확인
8. driver.get_log('performance') 호출 (보조)

결과: 실제 API 발견
  - https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon

성공 요인:
- JavaScript 인터셉터가 모든 fetch/XHR 호출을 캡처
- 동기적 실행으로 타이밍 문제 해결
- 필터링 로직 개선
```

---

## 8. 핵심 기술 개념 정리

### Performance 로그
- **정의**: Chrome DevTools Protocol의 네트워크 이벤트 로그
- **특징**: 비동기 수집, 브라우저 내부 버퍼 사용
- **한계**: 일부 요청 누락 가능, 타이밍 문제

### JavaScript 인터셉터
- **정의**: 함수 후킹을 통한 호출 가로채기
- **특징**: 동기적 실행, 100% 캡처 보장
- **장점**: 타이밍 문제 없음, 메모리 기반 저장

### 함수 후킹
- **원리**: 원본 함수를 변수에 저장 후 재정의
- **실행**: 재정의된 함수에서 원본 함수 호출
- **목적**: 호출 전후에 추가 로직 실행

### Selenium execute_script()
- **역할**: 브라우저 JavaScript 컨텍스트에서 코드 실행
- **용도**: 인터셉터 설치, 데이터 수집
- **특징**: Python-JavaScript 간 데이터 전달 가능

이제 각 개념의 기술적 세부사항을 이해하셨을 것입니다.

