# 왜 처음에 API를 찾지 못했는가?

## 🎯 발견한 API

```
https://gateway-kw.kakao.com/section/v2/timetables/days?placement={placement}
```

## ❌ 처음에 찾지 못한 이유

### 1. **Performance 로그의 한계**

**문제점:**
- Chrome의 Performance 로그는 모든 네트워크 요청을 캡처하지 못함
- 특히 XHR/Fetch 요청이 Performance 로그에 제대로 나타나지 않을 수 있음

**증거:**
- 첫 번째 시도에서 Performance 로그로는 추적/분석 API만 발견됨
- 실제 API 요청은 Performance 로그에 기록되지 않음

**해결책:**
- JavaScript 인터셉터 사용 (fetch/XHR 직접 후킹)
- 이 방법으로 실제 API 호출을 캡처할 수 있었음

### 2. **필터링 로직이 너무 엄격함**

**문제점:**
- 초기 필터링 로직이 `api`, `webtoon`, `chart` 같은 키워드만 찾음
- `gateway-kw.kakao.com` 도메인이 API 키워드 필터를 통과하지 못함
- `section/v2/timetables` 경로가 API 패턴으로 인식되지 않음

**원인:**
```python
# 초기 필터링 (너무 엄격)
if any(keyword in request_url.lower() for keyword in ['api', 'webtoon', 'chart']):
    # gateway-kw.kakao.com은 이 필터를 통과하지 못함
```

**해결책:**
- 카카오 도메인에 대해 더 관대한 필터링 적용
- JSON 응답인 경우도 포함

### 3. **타이밍 문제**

**문제점:**
- 버튼 클릭 후 JavaScript 실행 시간이 필요
- 네트워크 요청이 비동기로 발생
- 요청이 발생하기 전에 로그를 수집함

**증거:**
- 버튼 클릭 직후 로그를 수집하면 요청이 아직 발생하지 않음
- 3-5초 대기 후에도 일부 요청은 캡처되지 않음

**해결책:**
- 충분한 대기 시간 (5초 이상)
- 인터셉터를 사용하여 요청이 발생하는 즉시 캡처

### 4. **도메인 필터링 오류**

**문제점:**
- `kakaopagecdn.com`은 CDN으로 제외했지만
- `gateway-kw.kakao.com`은 실제 API 게이트웨이인데 제외될 수 있음

**원인:**
- 도메인 필터링 로직이 `kakao`를 포함한 모든 도메인을 제외할 수 있음
- 또는 `gateway` 키워드가 API 패턴으로 인식되지 않음

**해결책:**
- `gateway-kw.kakao.com` 같은 게이트웨이 도메인은 명시적으로 포함
- 카카오 도메인에 대해 더 세밀한 필터링

### 5. **JavaScript 인터셉터 미사용**

**가장 중요한 원인:**
- Performance 로그만으로는 부족
- JavaScript 레벨에서 직접 후킹해야 함

**성공한 방법:**
```javascript
// fetch와 XMLHttpRequest를 직접 후킹
window.fetch = function(...args) {
    window._apiCalls.push({
        type: 'fetch',
        url: args[0],
        method: args[1]?.method || 'GET'
    });
    return originalFetch.apply(this, args);
};
```

**이 방법이 성공한 이유:**
1. **직접 후킹**: 네트워크 레벨이 아닌 JavaScript 레벨에서 캡처
2. **모든 요청 캡처**: Performance 로그를 거치지 않고 직접 캡처
3. **타이밍 문제 해결**: 요청이 발생하는 즉시 캡처

## 📊 발견 과정 비교

### 첫 번째 시도 (실패)
- **방법**: Performance 로그만 사용
- **결과**: 추적/분석 API만 발견 (Facebook, Google Analytics 등)
- **원인**: 실제 API 요청이 Performance 로그에 기록되지 않음

### 두 번째 시도 (성공)
- **방법**: JavaScript 인터셉터 + Performance 로그
- **결과**: 실제 API 엔드포인트 발견
- **핵심**: `gateway-kw.kakao.com/section/v2/timetables/days`

## 🎓 교훈

1. **다양한 방법 시도**: Performance 로그만으로는 부족
2. **JavaScript 인터셉터**: 클라이언트 사이드 요청 캡처에 필수
3. **필터링 로직 개선**: 너무 엄격한 필터링은 오히려 방해
4. **충분한 대기 시간**: 비동기 요청을 위한 대기 시간 필요
5. **도메인 분석**: 게이트웨이 도메인을 명시적으로 포함

## ✅ 최종 해결책

**JavaScript 인터셉터 사용:**
- fetch와 XMLHttpRequest를 직접 후킹
- 모든 네트워크 요청을 JavaScript 레벨에서 캡처
- Performance 로그의 한계를 극복

**결과:**
- API 엔드포인트 발견: `gateway-kw.kakao.com/section/v2/timetables/days`
- 테스트 성공: 모든 요일/필터 조합에서 정상 작동
- 데이터 수집 가능: 이제 이 API를 사용하여 데이터 수집 가능

