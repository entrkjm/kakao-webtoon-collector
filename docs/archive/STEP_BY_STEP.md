# 단계별 설명: API를 어떻게 찾았나?

## 상황 설정

**목표**: 카카오 웹툰 사이트에서 "월요일" 버튼을 클릭했을 때 어떤 API가 호출되는지 알고 싶다.

---

## 방법 1: Performance 로그 시도 (실패)

### 무슨 일이 일어났나?

#### Step 1: 브라우저에 "일기장 쓰기" 요청
```python
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
```
**의미**: "브라우저야, 네트워크 요청할 때마다 일기장에 기록해줘"

#### Step 2: 페이지 열기
```python
driver.get('https://webtoon.kakao.com')
```
**의미**: 카카오 웹툰 사이트 열기

#### Step 3: 버튼 클릭
```python
button.click()
```
**의미**: "월요일" 버튼 클릭

**이때 실제로 일어나는 일:**
```
1. 버튼 클릭 이벤트 발생
2. JavaScript 코드 실행: fetch('https://gateway-kw.kakao.com/...')
3. 네트워크 요청 전송
4. 응답 받음
5. [나중에] 브라우저가 일기장에 기록 (비동기)
```

#### Step 4: 일기장 읽기
```python
time.sleep(5)  # 5초 대기
logs = driver.get_log('performance')  # 일기장 읽기
```

**문제**: 
- 5초를 기다렸지만 일기장에 기록이 없을 수 있음
- 브라우저가 나중에 기록할 수도 있음
- 너무 빨리 읽으면 기록이 없을 수 있음

**결과**: API를 찾지 못함

---

## 방법 2: 인터셉터 사용 (성공)

### 무슨 일이 일어났나?

#### Step 1: 페이지 열기
```python
driver.get('https://webtoon.kakao.com')
```

#### Step 2: 인터셉터 설치 (중요!)
```python
interceptor_script = """
window._apiCalls = [];  // 빈 배열 만들기 (기록용)

const originalFetch = window.fetch;  // 원래 fetch 함수 저장

window.fetch = function(...args) {  // fetch 함수를 우리 함수로 교체
    window._apiCalls.push({  // 기록에 추가
        url: args[0],
        method: 'GET'
    });
    return originalFetch.apply(this, args);  // 원래 fetch 실행
};
"""

driver.execute_script(interceptor_script)
```

**의미**:
- `window.fetch`는 브라우저가 제공하는 함수
- 이 함수를 우리가 만든 함수로 **교체**함
- 누군가 `fetch()`를 호출하면 우리 함수가 먼저 실행됨

#### Step 3: 버튼 클릭
```python
button.click()
```

**이때 실제로 일어나는 일:**
```
1. 버튼 클릭 이벤트 발생
2. JavaScript 코드 실행: fetch('https://gateway-kw.kakao.com/...')
   
   → 우리가 교체한 함수가 실행됨!
   → window._apiCalls.push({url: 'https://gateway-kw.kakao.com/...'}) 실행
   → 기록에 추가됨 (즉시!)
   
3. originalFetch.apply() 실행
   → 원래 fetch 함수 실행
   → 네트워크 요청 전송
```

#### Step 4: 기록 확인
```python
api_calls = driver.execute_script("return window._apiCalls;")
```

**결과**: 
```python
[
    {'url': 'https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon', 'method': 'GET'}
]
```

**성공!** API를 찾았음

---

## 핵심 차이점

### Performance 로그
```
fetch() 호출 → 네트워크 요청 → [나중에] 일기장에 기록 → 우리가 읽기
                              ↑
                         여기서 시간 차이 발생
```

### 인터셉터
```
fetch() 호출 → 우리 함수 실행 → 즉시 기록 → 원래 fetch 실행 → 네트워크 요청
              ↑
         여기서 즉시 기록 (시간 차이 없음)
```

---

## 함수 교체의 개념

### 일반적인 함수 사용
```javascript
// 브라우저가 제공하는 함수
window.fetch('https://api.com')
// → 네트워크 요청 전송
```

### 함수 교체 후
```javascript
// 1. 원래 함수 저장
const originalFetch = window.fetch;

// 2. 우리 함수로 교체
window.fetch = function(url) {
    console.log('누군가', url, '에 요청을 보냄!');  // 우리 코드
    return originalFetch(url);  // 원래 함수 실행
};

// 3. 누군가 fetch() 호출
window.fetch('https://api.com')
// → 우리 함수가 먼저 실행됨
// → "누군가 https://api.com 에 요청을 보냄!" 출력
// → 원래 fetch 실행
```

---

## apply()가 필요한 이유

### 문제 상황
```javascript
// args는 배열: ['https://api.com', {method: 'GET'}]
window.fetch = function(...args) {
    // args를 그대로 originalFetch에 전달하고 싶음
    // 하지만 originalFetch는 개별 인자로 받음
}
```

### 해결: apply() 사용
```javascript
// 방법 1: 직접 호출 (배열을 하나의 인자로 전달 - 잘못됨)
originalFetch(args)  // ❌ args는 배열이므로 하나의 인자로 전달됨

// 방법 2: apply() 사용 (배열을 개별 인자로 전달 - 올바름)
originalFetch.apply(this, args)  // ✅ args 배열의 각 요소를 개별 인자로 전달
```

**의미**:
- `apply(this, args)`는 `args` 배열을 펼쳐서 개별 인자로 전달
- `originalFetch.apply(this, ['url', options])` = `originalFetch('url', options)`

---

## 실제 발견 과정

### 첫 번째 시도
```python
# Performance 로그만 사용
logs = driver.get_log('performance')
# 결과: 추적 API만 발견 (Facebook, Google Analytics)
# 실제 API는 없음
```

### 두 번째 시도
```python
# 인터셉터 추가
driver.execute_script(interceptor_script)  # 인터셉터 설치
button.click()  # 버튼 클릭
api_calls = driver.execute_script("return window._apiCalls;")  # 기록 확인
# 결과: 실제 API 발견!
# https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon
```

---

## 요약

1. **Performance 로그**: 브라우저가 나중에 기록 (타이밍 문제)
2. **인터셉터**: 함수 호출 시점에 즉시 기록 (타이밍 문제 없음)
3. **결과**: 인터셉터로 API를 찾았음

**핵심**: 함수를 교체해서 호출을 가로채는 것이 성공의 열쇠였음

