-- ============================================================================
-- 카카오 웹툰 주간 차트 수집 파이프라인 - BigQuery 스키마 설정
-- ============================================================================
-- 
-- 이 스크립트는 BigQuery 데이터셋과 테이블을 생성합니다.
-- 
-- 실행 방법:
--   1. 데이터셋 생성: bq mk --dataset --location=asia-northeast3 PROJECT_ID:kakao_webtoon
--   2. 테이블 생성: bq query --use_legacy_sql=false < 이 파일
--   3. 또는 BigQuery 콘솔에서 직접 실행
--
-- ============================================================================

-- 데이터셋 생성 (수동 실행 필요)
-- bq mk --dataset --location=asia-northeast3 PROJECT_ID:kakao_webtoon

-- ============================================================================
-- 1. dim_webtoon 테이블 (웹툰 마스터 테이블)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `kakao-webtoon-collector.kakao_webtoon.dim_webtoon` (
  webtoon_id STRING NOT NULL,
  title STRING NOT NULL,
  author STRING,
  genre STRING,
  tags ARRAY<STRING>,
  seo_id STRING,
  adult BOOLEAN,
  catchphrase STRING,
  badges ARRAY<STRING>,
  content_id INT64,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
CLUSTER BY webtoon_id
OPTIONS(
  description="웹툰 기본 정보 마스터 테이블. webtoon_id는 고유해야 함."
);

-- 기존 테이블에 새 컬럼 추가 (이미 테이블이 있는 경우)
ALTER TABLE `kakao-webtoon-collector.kakao_webtoon.dim_webtoon`
ADD COLUMN IF NOT EXISTS seo_id STRING,
ADD COLUMN IF NOT EXISTS adult BOOLEAN,
ADD COLUMN IF NOT EXISTS catchphrase STRING,
ADD COLUMN IF NOT EXISTS badges ARRAY<STRING>,
ADD COLUMN IF NOT EXISTS content_id INT64;

-- ============================================================================
-- 2. fact_weekly_chart 테이블 (주간 차트 히스토리)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `kakao-webtoon-collector.kakao_webtoon.fact_weekly_chart` (
  chart_date DATE NOT NULL,
  webtoon_id STRING NOT NULL,
  rank INTEGER NOT NULL,
  collected_at TIMESTAMP NOT NULL,
  weekday STRING,
  year INTEGER NOT NULL,
  month INTEGER NOT NULL,
  week INTEGER NOT NULL,
  view_count INTEGER,
  sort_key STRING
)
PARTITION BY chart_date
CLUSTER BY webtoon_id, chart_date, sort_key
OPTIONS(
  description="주간 차트 순위 히스토리 테이블. chart_date로 파티션, (chart_date, webtoon_id, sort_key) 조합은 고유해야 함."
);

-- ============================================================================
-- 인덱스 및 제약 조건 (참고용)
-- ============================================================================
-- BigQuery는 자동으로 클러스터링을 사용하므로 별도 인덱스 생성 불필요
-- 
-- 제약 조건:
-- - dim_webtoon.webtoon_id는 고유해야 함 (애플리케이션 레벨에서 보장)
-- - fact_weekly_chart의 (chart_date, webtoon_id, sort_key) 조합은 고유해야 함
-- - fact_weekly_chart.webtoon_id는 dim_webtoon.webtoon_id를 참조해야 함 (Foreign Key)

