# chart_date 파라미터 문제 분석

> **작성일**: 2026-01-01  
> **문제**: `chart_date` 파라미터가 실제 API 호출에 영향을 주지 않음

---

## 🔍 문제 발견

사용자가 지적한 문제:
- 오늘이 2026년 1월 1일인데, 1월 1일부터 1월 4일까지 데이터를 수집했다는 것은 말이 안 됨
- `chart_date` 파라미터를 전달해도 실제로는 항상 현재 시점의 데이터만 수집됨

---

## 📊 확인 결과

### GCS 파일 생성 시간 확인

모든 파일이 같은 날(1월 1일)에 연속적으로 생성됨:
- `2026-01-01/webtoon_chart.json`: 2026-01-01 04:39:35 GMT
- `2026-01-02/webtoon_chart.json`: 2026-01-01 04:40:34 GMT
- `2026-01-03/webtoon_chart.json`: 2026-01-01 04:41:37 GMT
- `2026-01-04/webtoon_chart.json`: 2026-01-01 04:42:43 GMT
- `2026-01-05/webtoon_chart.json`: 2026-01-01 04:37:17 GMT

**결론**: 실제로는 같은 시점의 데이터를 다른 날짜로 저장한 것입니다.

---

## 🔎 원인 분석

### 1. API 엔드포인트 구조

카카오 웹툰 API:
```
https://gateway-kw.kakao.com/section/v2/timetables/days?placement={placement}
```

**파라미터**:
- `placement`: 요일 및 필터 정보 (예: `timetable_mon`, `timetable_tue`)
- **날짜 파라미터 없음**

### 2. 코드 확인

`try_api_endpoints` 함수 시그니처:
```python
def try_api_endpoints(
    weekday: Optional[str] = None,
    filter_type: Optional[str] = None,
    collect_all_weekdays: bool = False,
    sort_key: Optional[str] = None
) -> Optional[dict]:
```

**`chart_date` 파라미터가 없습니다!**

### 3. API 호출 흐름

1. `main.py`에서 `chart_date`를 받음
2. `try_api_endpoints`를 호출하지만 `chart_date`를 전달하지 않음
3. API는 항상 현재 시점의 데이터만 반환
4. 받은 데이터를 `chart_date`로 저장 (메타데이터일 뿐)

---

## ⚠️ 문제점

1. **과거 날짜 데이터 수집 불가**: 카카오 웹툰 API는 과거 날짜의 차트 데이터를 제공하지 않음
2. **`chart_date`는 메타데이터**: 실제 API 호출과 무관하게 저장 경로와 BigQuery의 `chart_date` 컬럼에만 사용됨
3. **데이터 정확성 문제**: 같은 시점의 데이터를 다른 날짜로 저장하면 데이터 분석에 오류 발생

---

## 💡 해결 방안

### 옵션 1: 현재 구조 유지 (권장)

**전제**: 카카오 웹툰 API는 과거 날짜의 차트 데이터를 제공하지 않음

**해결책**:
1. `chart_date`는 **수집 시점의 날짜**로만 사용
2. 과거 날짜로 수집 시도 시 경고 로그 출력
3. 문서에 명시: "카카오 웹툰 API는 항상 현재 시점의 데이터만 제공"

**코드 수정**:
```python
def try_api_endpoints(
    weekday: Optional[str] = None,
    filter_type: Optional[str] = None,
    collect_all_weekdays: bool = False,
    sort_key: Optional[str] = None,
    chart_date: Optional[date] = None  # 추가
) -> Optional[dict]:
    """
    주의: 카카오 웹툰 API는 과거 날짜의 차트 데이터를 제공하지 않습니다.
    chart_date는 메타데이터로만 사용되며, 항상 현재 시점의 데이터를 수집합니다.
    """
    if chart_date and chart_date < date.today():
        logger.warning(
            f"⚠️  과거 날짜({chart_date})로 수집 시도했지만, "
            f"API는 항상 현재 시점의 데이터만 제공합니다. "
            f"실제 수집 시점: {date.today()}"
        )
    # ... 기존 코드
```

### 옵션 2: 날짜 파라미터 추가 시도

API에 날짜 파라미터를 추가하여 시도:
```python
params = {
    'date': chart_date.strftime('%Y-%m-%d'),  # 시도
    'placement': placement
}
```

하지만 API가 지원하지 않을 가능성이 높습니다.

---

## 📝 권장 사항

1. **문서화**: 카카오 웹툰 API는 과거 날짜 데이터를 제공하지 않음을 명시
2. **경고 로그**: 과거 날짜로 수집 시도 시 경고 출력
3. **데이터 정확성**: `chart_date`는 실제 수집 시점의 날짜로만 사용
4. **스케줄러**: 매주 정해진 시간에 수집하여 정확한 날짜 데이터 확보

---

## 🔧 즉시 수정 사항

1. `try_api_endpoints`에 `chart_date` 파라미터 추가
2. 과거 날짜 수집 시도 시 경고 로그 출력
3. 문서 업데이트

---

**마지막 업데이트**: 2026-01-01

