# 카카오 웹툰 순위 집계 쿼리

> **작성일**: 2026-01-02  
> **목적**: 일일 수집 데이터를 연간 평균/중위 순위로 집계

---

## 개요

매일 수집된 데이터를 기반으로 연간 평균 순위와 중위 순위를 계산하는 쿼리입니다.

---

## 1. 연간 평균 순위 집계

### 기본 쿼리

```sql
-- 연간 평균 순위 계산 (전체 기간)
SELECT
  webtoon_id,
  AVG(rank) AS avg_rank,
  COUNT(*) AS collection_count,
  MIN(rank) AS best_rank,
  MAX(rank) AS worst_rank,
  STDDEV(rank) AS rank_stddev
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'  -- 정렬 옵션 선택
GROUP BY
  webtoon_id
ORDER BY
  avg_rank ASC  -- 평균 순위 오름차순 (1위가 가장 좋음)
LIMIT 100;
```

### 요일별 평균 순위

```sql
-- 요일별 평균 순위 계산
SELECT
  webtoon_id,
  weekday,
  AVG(rank) AS avg_rank,
  COUNT(*) AS collection_count
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'
GROUP BY
  webtoon_id,
  weekday
ORDER BY
  webtoon_id,
  weekday;
```

---

## 2. 연간 중위 순위 집계

### 기본 쿼리

```sql
-- 연간 중위 순위 계산 (PERCENTILE_CONT 사용)
SELECT
  webtoon_id,
  APPROX_QUANTILES(rank, 100)[OFFSET(50)] AS median_rank,
  COUNT(*) AS collection_count,
  MIN(rank) AS best_rank,
  MAX(rank) AS worst_rank
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'
GROUP BY
  webtoon_id
ORDER BY
  median_rank ASC
LIMIT 100;
```

### PERCENTILE_CONT 사용 (더 정확한 중위값)

```sql
-- PERCENTILE_CONT를 사용한 중위 순위 (BigQuery Standard SQL)
SELECT
  webtoon_id,
  PERCENTILE_CONT(rank, 0.5) OVER (PARTITION BY webtoon_id) AS median_rank,
  COUNT(*) OVER (PARTITION BY webtoon_id) AS collection_count
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'
GROUP BY
  webtoon_id,
  rank
ORDER BY
  median_rank ASC
LIMIT 100;
```

---

## 3. 웹툰 정보와 함께 조인

```sql
-- 웹툰 정보와 함께 평균 순위 조회
SELECT
  d.webtoon_id,
  d.title,
  d.author,
  AVG(f.rank) AS avg_rank,
  COUNT(*) AS collection_count,
  MIN(f.rank) AS best_rank,
  MAX(f.rank) AS worst_rank
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart` f
JOIN
  `kakao-webtoon-collector.kakao_webtoon.dim_webtoon` d
ON
  f.webtoon_id = d.webtoon_id
WHERE
  f.chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND f.sort_key = 'popularity'
GROUP BY
  d.webtoon_id,
  d.title,
  d.author
ORDER BY
  avg_rank ASC
LIMIT 100;
```

---

## 4. 월별/주별 집계

### 월별 평균 순위

```sql
-- 월별 평균 순위 추이
SELECT
  webtoon_id,
  DATE_TRUNC(chart_date, MONTH) AS month,
  AVG(rank) AS avg_rank,
  COUNT(*) AS collection_count
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'
GROUP BY
  webtoon_id,
  month
ORDER BY
  webtoon_id,
  month;
```

### 주별 평균 순위

```sql
-- 주별 평균 순위 추이
SELECT
  webtoon_id,
  DATE_TRUNC(chart_date, WEEK) AS week,
  AVG(rank) AS avg_rank,
  COUNT(*) AS collection_count
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'
GROUP BY
  webtoon_id,
  week
ORDER BY
  webtoon_id,
  week;
```

---

## 5. 정렬 옵션별 집계

```sql
-- 정렬 옵션별 평균 순위 비교
SELECT
  sort_key,
  webtoon_id,
  AVG(rank) AS avg_rank,
  COUNT(*) AS collection_count
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
GROUP BY
  sort_key,
  webtoon_id
ORDER BY
  sort_key,
  avg_rank ASC;
```

---

## 6. 요일별 순위 분포 분석

```sql
-- 요일별 순위 분포 (요일마다 어떤 웹툰이 높은 순위를 받는지)
SELECT
  weekday,
  webtoon_id,
  AVG(rank) AS avg_rank,
  COUNT(*) AS collection_count
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'
GROUP BY
  weekday,
  webtoon_id
ORDER BY
  weekday,
  avg_rank ASC;
```

---

## 7. 순위 변동성 분석

```sql
-- 순위 변동성이 큰 웹툰 (순위가 자주 변하는 웹툰)
SELECT
  webtoon_id,
  AVG(rank) AS avg_rank,
  STDDEV(rank) AS rank_stddev,
  (MAX(rank) - MIN(rank)) AS rank_range,
  COUNT(*) AS collection_count
FROM
  `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
WHERE
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  AND sort_key = 'popularity'
GROUP BY
  webtoon_id
HAVING
  collection_count >= 30  -- 최소 30회 이상 수집된 웹툰만
ORDER BY
  rank_stddev DESC  -- 변동성이 큰 순서대로
LIMIT 50;
```

---

## 8. 최종 연간 랭킹 (평균 순위 기준)

```sql
-- 최종 연간 랭킹 (평균 순위 기준, 오름차순)
WITH ranked_webtoons AS (
  SELECT
    d.webtoon_id,
    d.title,
    d.author,
    AVG(f.rank) AS avg_rank,
    COUNT(*) AS collection_count,
    MIN(f.rank) AS best_rank,
    MAX(f.rank) AS worst_rank,
    APPROX_QUANTILES(f.rank, 100)[OFFSET(50)] AS median_rank
  FROM
    `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart` f
  JOIN
    `kakao-webtoon-collector.kakao_webtoon.dim_webtoon` d
  ON
    f.webtoon_id = d.webtoon_id
  WHERE
    f.chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
    AND f.sort_key = 'popularity'
  GROUP BY
    d.webtoon_id,
    d.title,
    d.author
  HAVING
    collection_count >= 50  -- 최소 50회 이상 수집된 웹툰만
)
SELECT
  ROW_NUMBER() OVER (ORDER BY avg_rank ASC) AS final_rank,
  webtoon_id,
  title,
  author,
  avg_rank,
  median_rank,
  best_rank,
  worst_rank,
  collection_count
FROM
  ranked_webtoons
ORDER BY
  avg_rank ASC
LIMIT 100;
```

---

## 참고사항

1. **수집 빈도**: 매일 수집되므로 1년이면 약 365개의 데이터 포인트가 생성됩니다.
2. **요일별 차이**: 각 요일마다 다른 웹툰이 높은 순위를 받을 수 있으므로, 요일별 집계도 유용합니다.
3. **정렬 옵션**: `sort_key`에 따라 다른 순위가 나타나므로, 분석 시 정렬 옵션을 명시해야 합니다.
4. **데이터 품질**: 최소 수집 횟수 조건을 추가하여 신뢰성 있는 결과만 추출하는 것을 권장합니다.

---

**마지막 업데이트**: 2026-01-02
