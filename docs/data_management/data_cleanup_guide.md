# 카카오 웹툰 데이터 정리 가이드

> **작성일**: 2026-01-02  
> **목적**: 잘못된 정렬 로직으로 수집된 데이터 정리 및 재수집

---

## 문제 상황

1. **잘못된 정렬 로직**: `sorting.views` 값이 작을수록 순위가 높은데, 현재 코드는 큰 값이 먼저 오도록 정렬하고 있음
2. **잘못된 weekday_rank**: 정렬이 잘못되어 weekday_rank도 부정확함
3. **데이터 신뢰성**: 이런 데이터는 분석에 오히려 혼란을 줄 수 있음

---

## 정리 전략

### 전체 삭제 후 재수집 (권장)

**이유**:
- 데이터 양이 많지 않음 (약 5,661개 레코드, 4개 날짜)
- 정렬 로직이 잘못되어 모든 데이터가 의심스러움
- 재수집이 빠르고 간단함
- 깔끔한 시작점 확보

**유지할 데이터**:
- `dim_webtoon`: 웹툰 마스터 정보는 유지 (웹툰 ID, 제목, 작가 등은 변하지 않음)

**삭제할 데이터**:
- `fact_weekly_chart`: 모든 차트 데이터 삭제
- GCS 원본 파일: 선택적 삭제 (재수집 시 다시 생성됨)

---

## 실행 순서

### 1. 데이터 현황 확인

```bash
# BigQuery 데이터 확인
bq query --use_legacy_sql=false "
SELECT 
  COUNT(*) AS total_records,
  COUNT(DISTINCT chart_date) AS unique_dates,
  MIN(chart_date) AS earliest_date,
  MAX(chart_date) AS latest_date
FROM 
  \`kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart\`
"
```

### 2. BigQuery 데이터 삭제

```bash
cd kakao/scripts/data_management
./cleanup_incorrect_data.sh
```

또는 수동 실행:

```bash
bq query --use_legacy_sql=false "
DELETE FROM \`kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart\`
WHERE TRUE
"
```

### 3. GCS 원본 파일 삭제 (선택사항)

```bash
cd kakao/scripts/data_management
./cleanup_gcs_raw_data.sh
```

또는 수동 실행:

```bash
gsutil -m rm -r "gs://kakao-webtoon-raw/raw/**"
```

### 4. 정렬 로직 수정

- `sort_cards_by_sorting` 함수에서 `views` 정렬 시 `reverse=False`로 수정
- 다른 정렬 옵션들도 확인 및 수정

### 5. 데이터 재수집

```bash
# Cloud Functions 수동 실행
FUNCTION_URL=$(gcloud functions describe pipeline-function --gen2 --region=asia-northeast3 --format="value(serviceConfig.uri)")
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "sort_keys": ["popularity", "views", "createdAt", "popularityMale", "popularityFemale"],
    "collect_all_weekdays": true
  }'
```

### 6. 검증

```bash
cd kakao/scripts/test
./verify_weekday_rank.sh
```

---

## 주의사항

1. **dim_webtoon은 유지**: 웹툰 마스터 정보는 삭제하지 않습니다
2. **GCS 원본 파일**: 삭제해도 재수집 시 다시 생성되므로 선택사항입니다
3. **재수집 시간**: 모든 정렬 옵션 수집 시 약 5-10분 소요
4. **비용**: Always Free 범위 내에서 실행 가능

---

## 복구 방법

만약 실수로 삭제했다면:

1. **BigQuery**: 삭제된 데이터는 복구 불가 (백업이 없는 경우)
2. **GCS**: 삭제된 파일은 복구 불가 (버전 관리가 없는 경우)
3. **재수집**: 정렬 로직 수정 후 재수집 필요

---

## 검증 쿼리

재수집 후 데이터 검증:

```sql
-- 각 요일별 1위 웹툰 확인
SELECT 
  chart_date,
  weekday,
  sort_key,
  weekday_rank,
  rank AS global_rank,
  d.title,
  d.author
FROM 
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart` f
JOIN 
  `kakao-webtoon-collector.kakao_webtoon.dim_webtoon` d
ON 
  f.webtoon_id = d.webtoon_id
WHERE 
  chart_date = (SELECT MAX(chart_date) FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`)
  AND sort_key = 'popularity'
  AND weekday_rank = 1
ORDER BY 
  weekday;
```

---

**마지막 업데이트**: 2026-01-02
