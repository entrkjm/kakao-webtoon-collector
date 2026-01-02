# 한 줄씩 코드 설명

## 인터셉터 코드 전체

```javascript
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
```

---

## 각 줄 설명

### 1. `(function() { ... })();`
**의미**: 함수를 만들고 즉시 실행

**왜 필요한가?**
- 전역 변수를 만들지 않기 위해
- `originalFetch` 변수가 다른 코드와 충돌하지 않도록

**비유**: 
- 일반 함수: `function myFunc() { ... }` → 나중에 호출해야 함
- 즉시 실행 함수: `(function() { ... })()` → 만들자마자 실행

---

### 2. `const originalFetch = window.fetch;`
**의미**: 원래 fetch 함수를 `originalFetch` 변수에 저장

**설명**:
- `window.fetch`는 브라우저가 제공하는 함수
- 이 함수를 변수에 저장해둠 (나중에 사용하기 위해)

**예시**:
```javascript
// 원래 fetch 함수
window.fetch('https://api.com')  // 네트워크 요청 전송

// 함수를 변수에 저장
const originalFetch = window.fetch;

// 변수로도 호출 가능
originalFetch('https://api.com')  // 같은 결과
```

---

### 3. `window._apiCalls = [];`
**의미**: 빈 배열 만들기 (기록 저장용)

**설명**:
- `window._apiCalls`는 전역 변수
- 여기에 API 호출 기록을 저장함

**예시**:
```javascript
window._apiCalls = [];  // 빈 배열

// 나중에 추가
window._apiCalls.push({url: 'https://api.com'});
// 결과: [{url: 'https://api.com'}]
```

---

### 4. `window.fetch = function(...args) { ... }`
**의미**: fetch 함수를 우리가 만든 함수로 교체

**설명**:
- 원래 `window.fetch`는 브라우저가 제공하는 함수
- 이제 우리가 만든 함수로 교체됨
- 누군가 `fetch()`를 호출하면 우리 함수가 실행됨

**예시**:
```javascript
// 원래
window.fetch('https://api.com')  // 브라우저 함수 실행

// 교체 후
window.fetch = function(...args) {
    console.log('가로채기!');
    // 원래 함수 실행
};

window.fetch('https://api.com')  // 우리 함수 실행 → "가로채기!" 출력
```

---

### 5. `...args`
**의미**: 모든 인자를 배열로 받기

**설명**:
- `fetch(url, options)`처럼 여러 인자를 받을 수 있음
- `...args`는 모든 인자를 배열로 받음

**예시**:
```javascript
function myFunc(...args) {
    console.log(args);
}

myFunc('a', 'b', 'c');
// args = ['a', 'b', 'c']

myFunc('https://api.com', {method: 'GET'});
// args = ['https://api.com', {method: 'GET'}]
```

---

### 6. `window._apiCalls.push({ ... })`
**의미**: 기록 배열에 추가

**설명**:
- `push()`는 배열에 요소를 추가하는 메서드
- API 호출 정보를 객체로 만들어 배열에 추가

**예시**:
```javascript
window._apiCalls = [];

window._apiCalls.push({url: 'https://api.com', method: 'GET'});
// 결과: [{url: 'https://api.com', method: 'GET'}]

window._apiCalls.push({url: 'https://api2.com', method: 'POST'});
// 결과: [
//   {url: 'https://api.com', method: 'GET'},
//   {url: 'https://api2.com', method: 'POST'}
// ]
```

---

### 7. `args[0]`
**의미**: 첫 번째 인자 (URL)

**설명**:
- `fetch('https://api.com', options)`에서
- `args[0]` = `'https://api.com'` (첫 번째 인자)

**예시**:
```javascript
function myFunc(...args) {
    console.log(args[0]);  // 첫 번째 인자
    console.log(args[1]);  // 두 번째 인자
}

myFunc('https://api.com', {method: 'GET'});
// args[0] = 'https://api.com'
// args[1] = {method: 'GET'}
```

---

### 8. `args[1]?.method || 'GET'`
**의미**: 두 번째 인자의 method 속성, 없으면 'GET'

**설명**:
- `args[1]`은 두 번째 인자 (options 객체)
- `args[1]?.method`는 options.method (없으면 undefined)
- `|| 'GET'`는 없으면 'GET' 사용

**예시**:
```javascript
// 경우 1: method가 있는 경우
fetch('https://api.com', {method: 'POST'})
// args[1] = {method: 'POST'}
// args[1]?.method = 'POST'

// 경우 2: method가 없는 경우
fetch('https://api.com')
// args[1] = undefined
// args[1]?.method = undefined
// undefined || 'GET' = 'GET'
```

---

### 9. `return originalFetch.apply(this, args);`
**의미**: 원래 fetch 함수 호출

**설명**:
- `originalFetch`는 처음에 저장한 원래 fetch 함수
- `apply(this, args)`는 args 배열을 개별 인자로 전달
- 원래 fetch 함수를 실행해서 실제 네트워크 요청을 보냄

**예시**:
```javascript
// args = ['https://api.com', {method: 'GET'}]

// apply() 사용
originalFetch.apply(this, args)
// = originalFetch('https://api.com', {method: 'GET'})

// 직접 호출 (같은 결과)
originalFetch('https://api.com', {method: 'GET'})
```

**왜 apply()를 사용하는가?**
- `args`는 배열이므로 직접 전달할 수 없음
- `apply()`는 배열을 개별 인자로 펼쳐서 전달

---

## 전체 흐름

### 1. 인터셉터 설치
```python
driver.execute_script(interceptor_script)
```
**의미**: 브라우저에서 위의 JavaScript 코드 실행

**결과**: 
- `window.fetch`가 우리 함수로 교체됨
- `window._apiCalls` 배열이 생성됨

---

### 2. 버튼 클릭
```python
button.click()
```

**브라우저에서 일어나는 일:**
```javascript
// 카카오 웹툰 사이트의 JavaScript 코드 (추정)
function handleClick() {
    fetch('https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon')
        .then(response => response.json())
        .then(data => {
            // 데이터 처리
        });
}
```

**하지만 우리가 fetch를 교체했으므로:**
```javascript
// 1. fetch() 호출
fetch('https://gateway-kw.kakao.com/...')

// 2. 우리가 교체한 함수 실행
window.fetch = function(...args) {
    // args = ['https://gateway-kw.kakao.com/...', undefined]
    
    // 3. 기록에 추가
    window._apiCalls.push({
        type: 'fetch',
        url: args[0],  // 'https://gateway-kw.kakao.com/...'
        method: args[1]?.method || 'GET'  // 'GET'
    });
    
    // 4. 원래 fetch 실행
    return originalFetch.apply(this, args);
    // → 실제 네트워크 요청 전송
}
```

---

### 3. 기록 확인
```python
api_calls = driver.execute_script("return window._apiCalls;")
```

**의미**: 브라우저의 `window._apiCalls` 배열을 가져옴

**결과**:
```python
[
    {
        'type': 'fetch',
        'url': 'https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon',
        'method': 'GET'
    }
]
```

---

## 핵심 정리

1. **함수는 변수처럼 저장할 수 있음**
   ```javascript
   const originalFetch = window.fetch;
   ```

2. **함수는 교체할 수 있음**
   ```javascript
   window.fetch = function(...args) { ... };
   ```

3. **교체한 함수에서 원래 함수를 호출할 수 있음**
   ```javascript
   return originalFetch.apply(this, args);
   ```

4. **이렇게 하면 함수 호출을 가로챌 수 있음**
   - 누군가 `fetch()`를 호출하면
   - 우리 함수가 먼저 실행됨
   - 우리가 기록을 남김
   - 원래 함수를 실행해서 실제 요청을 보냄

---

## 왜 이 방법이 성공했나?

### Performance 로그
- 브라우저가 나중에 기록 (비동기)
- 우리가 읽을 때 기록이 없을 수 있음

### 인터셉터
- 함수 호출 시점에 즉시 기록 (동기)
- 항상 기록이 있음

**비유**:
- Performance 로그: 사진 찍기 (나중에 인화)
- 인터셉터: 실시간 녹화 (즉시 기록)

