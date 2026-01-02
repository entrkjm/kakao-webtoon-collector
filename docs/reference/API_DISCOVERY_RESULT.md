# 카카오 웹툰 API 발견 결과 및 원인 분석

## 🎉 발견한 API 엔드포인트

### 기본 API
```
https://gateway-kw.kakao.com/section/v2/timetables/days?placement={placement}
```

### Placement 파라미터 패턴
- **요일별 전체**: `timetable_{weekday}`
  - 예: `timetable_mon`, `timetable_tue`, `timetable_wed` 등
- **요일별 연재무료**: `timetable_{weekday}_free_publishing`
  - 예: `timetable_mon_free_publishing`
- **요일별 기다무**: `timetable_{weekday}_wait_free` (추정)

### 요일 매핑
- 월: `mon`
- 화: `tue`
- 수: `wed`
- 목: `thu`
- 금: `fri`
- 토: `sat`
- 일: `sun`

## API 응답 구조

```json
{
  "data": [
    {
      "id": "...",
      "title": "월",
      "module": "WEEKDAYS",
      "placement": "timetable_mon",
      "tag": "timetable_mon",
      "cardGroups": [
        {
          "cards": [
            {
              "id": "...",
              "key": "...",
              "content": {
                "title": "웹툰 제목",
                "author": "작가명",
                "catchphraseTwoLines": "...",
                "backgroundColor": "...",
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

## 왜 처음에 찾지 못했는가?

### 1. **Performance 로그의 한계**
- **문제**: Chrome의 Performance 로그는 모든 네트워크 요청을 캡처하지 못함
- **원인**: 
  - 일부 요청은 로그에 기록되지 않을 수 있음
  - XHR/Fetch 요청이 Performance 로그에 제대로 나타나지 않을 수 있음
- **해결**: JavaScript 인터셉터 사용 (fetch/XHR 직접 후킹)

### 2. **필터링 로직의 문제**
- **문제**: 초기 필터링 로직이 너무 엄격했음
- **원인**:
  - `gateway-kw.kakao.com` 도메인이 API 키워드 필터를 통과하지 못함
  - `section/v2/timetables` 경로가 API 패턴으로 인식되지 않음
- **해결**: 더 관대한 필터링 로직 적용

### 3. **타이밍 문제**
- **문제**: 요청이 발생하기 전에 로그를 수집함
- **원인**:
  - 버튼 클릭 후 JavaScript 실행 시간이 필요
  - 네트워크 요청이 비동기로 발생
- **해결**: 충분한 대기 시간과 인터셉터 사용

### 4. **도메인 필터링**
- **문제**: `gateway-kw.kakao.com`이 CDN이나 분석 도메인으로 오인될 수 있음
- **원인**: 
  - `kakaopagecdn.com`은 CDN으로 제외했지만
  - `gateway-kw.kakao.com`은 실제 API 게이트웨이
- **해결**: 도메인 필터링 로직 개선

## 발견 방법

### 성공한 방법: JavaScript 인터셉터
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

이 방법이 성공한 이유:
1. **직접 후킹**: 네트워크 레벨이 아닌 JavaScript 레벨에서 캡처
2. **모든 요청 캡처**: Performance 로그를 거치지 않고 직접 캡처
3. **타이밍 문제 해결**: 요청이 발생하는 즉시 캡처

## API 사용 방법

### 예제 코드
```python
import requests

url = "https://gateway-kw.kakao.com/section/v2/timetables/days"
params = {
    'placement': 'timetable_mon_free_publishing'  # 월요일 연재무료
}

headers = {
    'User-Agent': 'Mozilla/5.0 ...',
    'Referer': 'https://webtoon.kakao.com/',
    'Origin': 'https://webtoon.kakao.com'
}

response = requests.get(url, params=params, headers=headers)
data = response.json()
```

## 다음 단계

1. **API 파싱 로직 구현**: `parse_api.py` 수정
2. **extract.py 수정**: API 호출 로직 추가
3. **로컬 테스트**: 실제 데이터 수집 테스트
4. **정렬 옵션 확인**: 정렬 API 엔드포인트 찾기

## 교훈

1. **다양한 방법 시도**: Performance 로그만으로는 부족
2. **JavaScript 인터셉터**: 클라이언트 사이드 요청 캡처에 효과적
3. **필터링 로직 개선**: 너무 엄격한 필터링은 오히려 방해
4. **충분한 대기 시간**: 비동기 요청을 위한 대기 시간 필요

