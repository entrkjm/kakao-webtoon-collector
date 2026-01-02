# 카카오 vs 네이버 웹툰 스키마 비교

> **작성일**: 2026-01-01  
> **목적**: 카카오 웹툰 API 응답 구조에 맞춰 스키마 확장

---

## 현재 카카오 웹툰 스키마 (dim_webtoon)

```python
- webtoon_id: STRING (card.id)
- title: STRING (content.title)
- author: STRING (content.authors에서 AUTHOR 타입만)
- genre: STRING (NULL - 수집 안 함)
- tags: ARRAY<STRING> (NULL - 수집 안 함)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

---

## 카카오 웹툰 API에서 제공하는 필드

### 현재 수집 중인 필드
- `card.id` → `webtoon_id`
- `content.title` → `title`
- `content.authors` (AUTHOR 타입만) → `author`

### 수집 가능하지만 미수집인 필드
- `card.genreFilters` → `genre` (예: ["all", "ACTION_WUXIA"])
- `content.seoKeywords` → `tags` (예: ["#역동적인", "#감동적인", "#액션/무협", "#가족물"])
- `content.seoId` → `seo_id` (예: "대사형-선유")
- `content.adult` → `adult` (boolean)
- `content.catchphraseTwoLines` → `catchphrase` (예: "무영문의 대사형 선유.\n그런 그의 우직한 강호이야기.")
- `content.badges` → `badges` (예: ["FREE_PUBLISHING"])
- `content.id` → `content_id` (숫자 ID, 예: 2589)

---

## 네이버 웹툰 스키마 (참고)

```python
- webtoon_id: STRING
- title: STRING
- author: STRING
- genre: STRING
- tags: ARRAY<STRING>
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

네이버는 `genre`와 `tags`를 수집하지만, 카카오는 현재 수집하지 않음.

---

## 제안하는 카카오 웹툰 확장 스키마

```python
- webtoon_id: STRING (card.id) - 필수
- title: STRING (content.title) - 필수
- author: STRING (content.authors에서 AUTHOR 타입만) - 선택
- genre: STRING (card.genreFilters에서 "all" 제외한 첫 번째 값) - 선택
- genres: ARRAY<STRING> (card.genreFilters 전체) - 선택
- tags: ARRAY<STRING> (content.seoKeywords에서 "#" 제거) - 선택
- seo_id: STRING (content.seoId) - 선택
- adult: BOOLEAN (content.adult) - 선택
- catchphrase: STRING (content.catchphraseTwoLines) - 선택
- badges: ARRAY<STRING> (content.badges의 title 리스트) - 선택
- content_id: INTEGER (content.id) - 선택
- created_at: TIMESTAMP - 필수
- updated_at: TIMESTAMP - 필수
```

---

## 필드 매핑 상세

### genre
- **소스**: `card.genreFilters`
- **예시**: `["all", "ACTION_WUXIA"]` → `"ACTION_WUXIA"`
- **로직**: "all"을 제외한 첫 번째 값 사용

### genres (새 필드)
- **소스**: `card.genreFilters`
- **예시**: `["all", "ACTION_WUXIA"]` → `["ACTION_WUXIA"]` (또는 전체)
- **로직**: "all" 제외한 모든 값

### tags
- **소스**: `content.seoKeywords`
- **예시**: `["#역동적인", "#감동적인", "#액션/무협", "#가족물"]` → `["역동적인", "감동적인", "액션/무협", "가족물"]`
- **로직**: "#" 제거

### seo_id
- **소스**: `content.seoId`
- **예시**: `"대사형-선유"`

### adult
- **소스**: `content.adult`
- **예시**: `false` 또는 `true`

### catchphrase
- **소스**: `content.catchphraseTwoLines`
- **예시**: `"무영문의 대사형 선유.\n그런 그의 우직한 강호이야기."`

### badges
- **소스**: `content.badges`
- **예시**: `[{"title": "FREE_PUBLISHING", ...}]` → `["FREE_PUBLISHING"]`
- **로직**: badges 배열에서 title만 추출

### content_id
- **소스**: `content.id`
- **예시**: `2589`

---

## 마이그레이션 계획

1. **스키마 확장**: BigQuery 테이블에 새 컬럼 추가 (ALTER TABLE)
2. **파싱 로직 수정**: `parse_api.py`에서 새 필드 추출
3. **모델 수정**: `models.py`의 `create_dim_webtoon_record` 함수 확장
4. **기존 데이터**: NULL로 유지 (또는 재수집)

---

**마지막 업데이트**: 2026-01-01

