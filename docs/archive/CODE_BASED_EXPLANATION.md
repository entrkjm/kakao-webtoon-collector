# 카카오 웹툰 API 발견 - 코드 기반 기술 설명

## 1. Performance 로그의 내부 동작

### Chrome DevTools Protocol

#### 로그 활성화
```python
# ChromeOptions에 Performance 로그 활성화 설정
chrome_options = Options()
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
```

**내부 동작:**
- Chrome DevTools Protocol의 `Log.enable` 명령 실행
- `performance` 로그 레벨을 `ALL`로 설정
- 브라우저가 네트워크 이벤트를 로그 버퍼에 기록

#### 로그 수집
```python
logs = driver.get_log('performance')
```

**내부 동작:**
1. Selenium이 Chrome DevTools Protocol의 `Log.getEntries` 명령 실행
2. 브라우저의 로그 버퍼에서 `performance` 타입 로그 읽기
3. 로그 엔트리를 Python 리스트로 변환하여 반환

#### 로그 엔트리 구조
```python
log_entry = {
    'level': 'INFO',  # 로그 레벨
    'message': '{"message":{"method":"Network.responseReceived",...}}',  # JSON 문자열
    'timestamp': 1767190200937  # 타임스탬프 (밀리초)
}
```

**message 필드 파싱:**
```python
import json

# message는 JSON 문자열이므로 파싱 필요
message_obj = json.loads(log_entry['message'])
# {
#   "message": {
#     "method": "Network.responseReceived",
#     "params": {
#       "response": {
#         "url": "https://example.com",
#         "status": 200,
#         "mimeType": "application/json"
#       }
#     }
#   }
# }
```

### Performance 로그의 한계: 비동기 수집

#### 문제 상황
```python
# 시나리오: 버튼 클릭 후 API 호출

# T0: 버튼 클릭
driver.execute_script("arguments[0].click();", button)

# T1: JavaScript 이벤트 핸들러 실행
# 페이지의 JavaScript 코드:
#   button.addEventListener('click', () => {
#     fetch('https://gateway-kw.kakao.com/...')
#   })

# T2: fetch() 호출 (JavaScript 실행 컨텍스트)
# T3: 네트워크 요청 전송 (브라우저 엔진)
# T4: HTTP 응답 수신
# T5: Performance 로그에 이벤트 추가 (비동기, 큐에 추가)
#     - 브라우저 내부 로그 버퍼에 추가
#     - 이 작업은 메인 스레드와 별도로 실행될 수 있음

# T6: 우리가 로그 읽기
time.sleep(3)  # 3초 대기
logs = driver.get_log('performance')  # 로그 버퍼 읽기

# 문제: T5와 T6의 실행 순서가 보장되지 않음
# - T6가 T5보다 먼저 실행되면 요청을 놓침
# - 로그 버퍼가 이미 비워졌을 수 있음
```

#### 실제 코드에서의 증거
```python
# 첫 번째 시도
driver.get_log('performance')  # 로그 버퍼 비우기
button.click()
time.sleep(5)
logs = driver.get_log('performance')  # 새 로그 읽기

# 결과: API 요청이 로그에 없음
# 원인: 로그 버퍼에 기록되기 전에 읽었거나, 버퍼가 비워짐
```

---

## 2. JavaScript 인터셉터의 메커니즘

### 함수 후킹의 실행 흐름

#### 원본 코드 (카카오 웹툰 사이트)
```javascript
// 페이지가 로드될 때 실행되는 코드 (추정)
function handleWeekdayClick(weekday) {
    const url = `https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_${weekday}`;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            // 데이터 처리
        });
}
```

#### 인터셉터 설치 (우리 코드)
```python
interceptor_script = """
(function() {
    // 1. 원본 함수 저장
    const originalFetch = window.fetch;
    
    // 2. 전역 배열 초기화 (호출 기록용)
    window._apiCalls = [];
    
    // 3. fetch 함수 재정의
    window.fetch = function(...args) {
        // args[0]: URL (문자열)
        // args[1]: options 객체 (선택적)
        
        const url = args[0];
        const options = args[1] || {};
        const method = options.method || 'GET';
        
        // 4. 호출 정보 저장 (동기적으로 실행됨)
        window._apiCalls.push({
            type: 'fetch',
            url: url,
            method: method,
            timestamp: Date.now()
        });
        
        // 5. 원본 함수 호출 (실제 네트워크 요청 수행)
        return originalFetch.apply(this, args);
    };
})();
"""

# Selenium으로 브라우저에서 실행
driver.execute_script(interceptor_script)
```

#### 실행 흐름
```
1. 페이지 로드
2. execute_script() 실행 → 인터셉터 설치
3. 사용자가 버튼 클릭
4. handleWeekdayClick() 실행
5. fetch() 호출
   → 우리가 재정의한 함수 실행
   → window._apiCalls.push() 실행 (즉시, 동기)
   → originalFetch.apply() 실행 (네트워크 요청)
6. 우리가 execute_script("return window._apiCalls") 실행
   → 배열 반환 (모든 호출 기록 포함)
```

### apply() 메서드의 역할

#### 함수 호출 방식 비교
```javascript
// 방법 1: 일반 호출
originalFetch(url, options);

// 방법 2: call() 사용
originalFetch.call(this, url, options);

// 방법 3: apply() 사용 (우리가 사용한 방법)
originalFetch.apply(this, [url, options]);

// 방법 4: 스프레드 연산자
originalFetch(...args);
```

#### 왜 apply()를 사용하는가?
```javascript
// args는 배열: ['https://api.com', {method: 'GET'}]
window.fetch = function(...args) {
    // args를 그대로 전달해야 함
    // 하지만 originalFetch는 개별 인자로 받음
    
    // ❌ 잘못된 방법
    return originalFetch(args);  // 배열을 하나의 인자로 전달
    
    // ✅ 올바른 방법
    return originalFetch.apply(this, args);  // 배열을 개별 인자로 전달
};
```

**apply()의 동작:**
```javascript
// apply(thisArg, argsArray)
originalFetch.apply(this, ['https://api.com', {method: 'GET'}])
// 내부적으로 다음과 같이 실행됨:
// originalFetch('https://api.com', {method: 'GET'})
```

### this 바인딩

#### this의 의미
```javascript
window.fetch = function(...args) {
    // this는 함수가 호출된 컨텍스트를 가리킴
    // window.fetch()로 호출되면 this === window
    // obj.fetch()로 호출되면 this === obj
    
    // 원본 fetch도 같은 컨텍스트에서 호출되어야 함
    return originalFetch.apply(this, args);
    // this를 전달하여 원본 함수의 컨텍스트 유지
};
```

---

## 3. XMLHttpRequest.prototype.open 후킹

### 프로토타입 체인

#### XMLHttpRequest의 구조
```javascript
// XMLHttpRequest는 생성자 함수
function XMLHttpRequest() {
    // 인스턴스 생성
}

// 프로토타입에 메서드 정의
XMLHttpRequest.prototype.open = function(method, url, ...args) {
    // 실제 구현
};

// 사용
const xhr = new XMLHttpRequest();
xhr.open('GET', 'https://api.com');  // 프로토타입의 open 메서드 호출
```

#### 프로토타입 메서드 후킹
```javascript
// 원본 메서드 저장
const originalOpen = XMLHttpRequest.prototype.open;

// 프로토타입 메서드 재정의
XMLHttpRequest.prototype.open = function(method, url, ...args) {
    // 모든 XMLHttpRequest 인스턴스가 이 메서드를 사용하게 됨
    
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

#### 인스턴스별 동작
```javascript
const xhr1 = new XMLHttpRequest();
xhr1.open('GET', 'https://api1.com');  
// → XMLHttpRequest.prototype.open 호출
// → 우리가 후킹한 함수 실행
// → window._apiCalls에 기록

const xhr2 = new XMLHttpRequest();
xhr2.open('POST', 'https://api2.com');
// → 같은 프로토타입 메서드 사용
// → window._apiCalls에 기록
```

---

## 4. Selenium execute_script()의 동작

### 브라우저 컨텍스트에서 실행

#### JavaScript 실행 컨텍스트
```python
# Python 코드
driver.execute_script("window.myVar = 'hello';")

# 브라우저에서 실행되는 JavaScript:
# window.myVar = 'hello';
# 이 코드는 브라우저의 전역 객체(window)에 접근
```

#### 데이터 반환
```python
# JavaScript에서 Python으로 데이터 전달
result = driver.execute_script("""
    return {
        url: 'https://api.com',
        status: 200,
        data: [1, 2, 3]
    };
""")

# result는 Python dict로 변환됨
# {
#     'url': 'https://api.com',
#     'status': 200,
#     'data': [1, 2, 3]
# }
```

#### 배열 반환
```python
# JavaScript 배열
api_calls = driver.execute_script("return window._apiCalls || [];")

# Python 리스트로 변환
# [
#     {'type': 'fetch', 'url': 'https://api.com', 'method': 'GET'},
#     {'type': 'xhr', 'url': 'https://api2.com', 'method': 'POST'}
# ]
```

### 실행 시점

#### 페이지 로드 전 실행
```python
driver.get(KAKAO_WEBTOON_URL)  # 페이지 로드
time.sleep(2)  # 페이지 로드 대기

# 인터셉터 설치 (페이지 로드 후, 버튼 클릭 전)
driver.execute_script(interceptor_script)

# 이제 모든 fetch/XHR 호출이 캡처됨
button.click()
```

**중요:** 인터셉터는 실제 API 호출이 발생하기 전에 설치되어야 함

---

## 5. 왜 Performance 로그로는 찾지 못했는가?

### 기술적 원인 분석

#### 원인 1: 로그 버퍼의 비동기 특성
```python
# 브라우저 내부 동작 (단순화)
class PerformanceLogBuffer:
    def __init__(self):
        self.buffer = []
        self.max_size = 1000
    
    def add_event(self, event):
        # 비동기적으로 실행될 수 있음
        # 메인 스레드와 별도 스레드에서 실행
        self.buffer.append(event)
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)  # 오래된 로그 제거
    
    def get_events(self):
        # 현재 버퍼의 모든 이벤트 반환
        return self.buffer.copy()
```

**문제:**
- `add_event()`와 `get_events()` 사이의 동기화 문제
- 버퍼 크기 제한으로 오래된 로그 손실
- 메인 스레드와 별도 스레드에서 실행되어 타이밍 문제

#### 원인 2: 이벤트 기록 조건
```python
# Chrome의 Performance 로그 기록 조건 (추정)
def should_log_event(request):
    # 일부 요청은 로그에 기록하지 않음
    if request.is_cors_preflight():
        return False  # OPTIONS 요청은 기록하지 않음
    
    if request.is_service_worker():
        return False  # Service Worker 요청은 별도 로그
    
    if request.is_too_fast():
        return False  # 너무 빠른 요청은 기록하지 않을 수 있음
    
    return True
```

#### 원인 3: 필터링 로직의 문제
```python
# 초기 필터링 (너무 엄격)
def is_api_candidate(url):
    keywords = ['api', 'webtoon', 'chart']
    return any(kw in url.lower() for kw in keywords)

# 테스트
url = "https://gateway-kw.kakao.com/section/v2/timetables/days"
is_api_candidate(url)  # False
# 'api', 'webtoon', 'chart' 중 어느 것도 URL에 없음
```

---

## 6. 왜 인터셉터가 성공했는가?

### 동기적 실행 보장

#### 실행 흐름 비교
```javascript
// Performance 로그 (비동기)
fetch('https://api.com')
  → 네트워크 요청 전송
  → 응답 수신
  → [비동기] Performance 로그에 기록
  → [나중에] 우리가 로그 읽기

// 인터셉터 (동기)
fetch('https://api.com')
  → 우리가 재정의한 함수 실행 (즉시)
  → window._apiCalls.push() 실행 (즉시, 동기)
  → originalFetch.apply() 실행
  → [나중에] 우리가 window._apiCalls 읽기
```

**핵심 차이:**
- Performance 로그: 이벤트 기록이 비동기 (타이밍 문제)
- 인터셉터: 함수 호출 시점에 즉시 실행 (타이밍 문제 없음)

### 메모리 직접 접근

#### Performance 로그
```python
# 브라우저 내부 버퍼에서 읽기
logs = driver.get_log('performance')
# → Chrome DevTools Protocol 명령 실행
# → 네트워크 레이어를 거쳐야 함
# → 지연 가능
```

#### 인터셉터
```python
# JavaScript 변수에서 직접 읽기
api_calls = driver.execute_script("return window._apiCalls;")
# → JavaScript 실행 컨텍스트에서 직접 접근
# → 네트워크 레이어를 거치지 않음
# → 즉시 반환
```

---

## 7. 실제 발견 과정

### 첫 번째 시도 코드
```python
# Performance 로그만 사용
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
driver.get(KAKAO_WEBTOON_URL)
button.click()
time.sleep(5)
logs = driver.get_log('performance')

# 결과: 추적 API만 발견
# - Facebook Pixel
# - Google Analytics
# - 실제 API는 없음
```

### 두 번째 시도 코드
```python
# 인터셉터 추가
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

driver.get(KAKAO_WEBTOON_URL)
driver.execute_script(interceptor_script)  # 인터셉터 설치
button.click()
time.sleep(3)
api_calls = driver.execute_script("return window._apiCalls;")

# 결과: 실제 API 발견
# - https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon
```

---

## 8. 핵심 정리

### Performance 로그
- **메커니즘**: Chrome DevTools Protocol을 통한 비동기 로그 수집
- **저장 위치**: 브라우저 내부 로그 버퍼
- **접근 방식**: Selenium을 통한 비동기 읽기
- **한계**: 타이밍 문제, 일부 요청 누락 가능

### JavaScript 인터셉터
- **메커니즘**: 함수 후킹을 통한 동기적 호출 가로채기
- **저장 위치**: JavaScript 변수 (window._apiCalls)
- **접근 방식**: execute_script()로 직접 접근
- **장점**: 100% 캡처 보장, 타이밍 문제 없음

### 성공 요인
1. **동기적 실행**: 함수 호출 시점에 즉시 실행
2. **메모리 직접 접근**: 네트워크 레이어를 거치지 않음
3. **필터링 불필요**: 모든 호출을 캡처한 후 필터링

이제 각 기술 개념의 내부 동작을 이해하셨을 것입니다.

