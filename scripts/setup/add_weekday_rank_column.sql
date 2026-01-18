-- ============================================================================
-- weekday_rank 컬럼 추가 및 기존 데이터 마이그레이션
-- ============================================================================
-- 
-- 문제: 현재 rank는 통합 순위(global rank)로 저장되어 수집 시점의 요일에 따라 편향됨
-- 해결: 요일별 순위(weekday_rank) 컬럼 추가
--
-- 실행 방법:
--   bq query --use_legacy_sql=false < 이 파일
--
-- ============================================================================

-- 1. weekday_rank 컬럼 추가
ALTER TABLE `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
ADD COLUMN IF NOT EXISTS weekday_rank INTEGER;

-- 2. 기존 데이터 마이그레이션: 요일별 순위 재계산
-- 각 (chart_date, weekday, sort_key) 그룹 내에서 rank 순서로 요일별 순위 계산
UPDATE `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart` f
SET weekday_rank = (
  SELECT rn
  FROM (
    SELECT 
      webtoon_id,
      ROW_NUMBER() OVER (PARTITION BY chart_date, weekday, COALESCE(sort_key, '') ORDER BY rank) AS rn
    FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
    WHERE chart_date = f.chart_date 
      AND weekday = f.weekday
      AND COALESCE(sort_key, '') = COALESCE(f.sort_key, '')
  ) ranked
  WHERE ranked.webtoon_id = f.webtoon_id
)
WHERE weekday_rank IS NULL;

-- 3. 컬럼 설명 추가
ALTER TABLE `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
ALTER COLUMN weekday_rank SET OPTIONS(description="요일별 순위 (각 요일 내에서 1, 2, 3, ... 순위)");

-- ============================================================================
-- 검증 쿼리
-- ============================================================================
-- 다음 쿼리로 마이그레이션 결과 확인:
--
-- SELECT 
--   chart_date,
--   weekday,
--   sort_key,
--   COUNT(*) AS total,
--   COUNT(weekday_rank) AS with_weekday_rank,
--   MIN(weekday_rank) AS min_rank,
--   MAX(weekday_rank) AS max_rank
-- FROM `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart`
-- GROUP BY chart_date, weekday, sort_key
-- ORDER BY chart_date DESC, weekday, sort_key
