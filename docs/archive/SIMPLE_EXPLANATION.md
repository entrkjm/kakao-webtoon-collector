# 카카오 웹툰 API 발견 - 쉽게 설명하기

## 문제 상황

**목표**: 카카오 웹툰 사이트에서 웹툰 목록을 가져오는 API를 찾고 싶다.

**문제**: 버튼을 클릭했을 때 어떤 API가 호출되는지 모른다.

---

## 방법 1: Performance 로그 (실패한 방법)

### 개념
브라우저가 "어떤 웹사이트에 요청을 보냈는지" 기록하는 일기장이라고 생각하세요.

### 작동 방식
```
1. 브라우저가 웹사이트에 요청을 보냄
2. 브라우저가 일기장에 "어떤 사이트에 요청을 보냈다"고 기록
3. 우리가 나중에 일기장을 읽음
```

### 코드
```python
# 1. 일기장 쓰기 시작하라고 브라우저에 요청
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

# 2. 버튼 클릭 (이때 API 호출 발생)
button.click()

# 3. 일기장 읽기
logs = driver.get_log('performance')
```

### 왜 실패했나?
**문제 1: 타이밍 문제**
```
시간 순서:
1. 버튼 클릭
2. API 호출 발생
3. 브라우저가 일기장에 기록 (나중에 기록할 수도 있음)
4. 우리가 일기장 읽기 (너무 빨리 읽으면 기록이 없을 수 있음)
```

**문제 2: 일부 요청이 기록되지 않음**
- 브라우저가 모든 요청을 기록하지 않을 수 있음
- 너무 빠른 요청은 기록되지 않을 수 있음

---

## 방법 2: JavaScript 인터셉터 (성공한 방법)

### 개념
JavaScript의 `fetch()` 함수를 가로채서, 누가 어디에 요청을 보내는지 기록하는 방법입니다.

### 비유
택배 배송을 예로 들면:
- **원래 방식**: 택배가 배송되는 것을 멀리서 관찰 (Performance 로그)
- **인터셉터 방식**: 택배 회사에 들어가서 "누가 어디로 택배를 보내는지" 직접 기록 (인터셉터)

### 작동 원리

#### Step 1: 원본 함수 저장
```javascript
// 원래 fetch 함수를 변수에 저장 (나중에 사용하기 위해)
const originalFetch = window.fetch;
```

**의미**: 
- `window.fetch`는 브라우저가 제공하는 함수
- 이 함수를 `originalFetch` 변수에 저장해둠

#### Step 2: 함수 교체
```javascript
// fetch 함수를 우리가 만든 함수로 교체
window.fetch = function(...args) {
    // args[0] = URL (예: 'https://api.com')
    // args[1] = 옵션 (예: {method: 'GET'})
    
    // 1. 누가 어디에 요청을 보내는지 기록
    window._apiCalls.push({
        url: args[0],
        method: args[1]?.method || 'GET'
    });
    
    // 2. 원래 fetch 함수 호출 (실제 요청은 여전히 보냄)
    return originalFetch.apply(this, args);
};
```

**의미**:
- 누군가 `fetch('https://api.com')`을 호출하면
- 우리가 만든 함수가 먼저 실행됨
- 우리 함수가 URL을 기록한 후
- 원래 fetch 함수를 호출해서 실제 요청을 보냄

#### Step 3: 기록 확인
```python
# 브라우저에서 기록을 가져옴
api_calls = driver.execute_script("return window._apiCalls;")
# 결과: [{'url': 'https://gateway-kw.kakao.com/...', 'method': 'GET'}]
```

---

## 왜 인터셉터가 성공했나?

### 차이점 비교

#### Performance 로그
```
1. 버튼 클릭
2. fetch() 함수 실행
3. 네트워크 요청 전송
4. [나중에] 브라우저가 일기장에 기록
5. 우리가 일기장 읽기

문제: 4번과 5번 사이에 시간 차이가 있음
```

#### 인터셉터
```
1. 버튼 클릭
2. fetch() 함수 실행
   → 우리가 교체한 함수가 실행됨 (즉시)
   → 기록에 추가 (즉시)
3. 원래 fetch 함수 실행 (네트워크 요청)
4. 우리가 기록 읽기

장점: 2번에서 즉시 기록되므로 타이밍 문제 없음
```

---

## 실제 코드 흐름

### 전체 과정
```python
# 1. 브라우저 열기
driver = webdriver.Chrome()

# 2. 페이지 로드
driver.get('https://webtoon.kakao.com')

# 3. 인터셉터 설치 (중요: 버튼 클릭 전에!)
interceptor_script = """
window._apiCalls = [];
const originalFetch = window.fetch;
window.fetch = function(...args) {
    window._apiCalls.push({url: args[0], method: 'GET'});
    return originalFetch.apply(this, args);
};
"""
driver.execute_script(interceptor_script)

# 4. 버튼 클릭 (이때 fetch() 호출됨)
button.click()

# 5. 기록 확인
api_calls = driver.execute_script("return window._apiCalls;")
# 결과: [{'url': 'https://gateway-kw.kakao.com/...', 'method': 'GET'}]
```

---

## 핵심 개념 정리

### 1. 함수는 변수처럼 저장할 수 있다
```javascript
// 함수를 변수에 저장
const myFunction = window.fetch;

// 나중에 사용
myFunction('https://api.com');
```

### 2. 함수를 교체할 수 있다
```javascript
// 원래 함수
window.fetch = function(url) { ... }

// 우리가 만든 함수로 교체
window.fetch = function(url) {
    // 우리 코드
    // 원래 함수 호출
}
```

### 3. apply()는 함수를 호출하는 방법
```javascript
// 일반 호출
originalFetch('https://api.com', {method: 'GET'});

// apply()로 호출 (배열을 인자로 전달)
originalFetch.apply(this, ['https://api.com', {method: 'GET'}]);
```

---

## 발견한 API

### API 주소
```
https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon
```

### 의미
- `gateway-kw.kakao.com`: 카카오의 게이트웨이 서버
- `/section/v2/timetables/days`: 시간표 일별 데이터를 가져오는 API
- `?placement=timetable_mon`: 월요일 데이터를 요청

### 사용 방법
```python
import requests

url = "https://gateway-kw.kakao.com/section/v2/timetables/days"
params = {'placement': 'timetable_mon'}

response = requests.get(url, params=params)
data = response.json()  # 웹툰 목록 데이터
```

---

## 왜 처음에 못 찾았나? (간단 요약)

1. **Performance 로그의 한계**
   - 브라우저가 나중에 기록할 수도 있음
   - 우리가 너무 빨리 읽으면 기록이 없을 수 있음

2. **인터셉터의 장점**
   - 함수 호출 시점에 즉시 기록
   - 타이밍 문제 없음

3. **결론**
   - Performance 로그: 관찰자 (나중에 기록)
   - 인터셉터: 직접 참여자 (즉시 기록)

