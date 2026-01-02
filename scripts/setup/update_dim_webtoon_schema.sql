-- ============================================================================
-- dim_webtoon 테이블 스키마 업데이트
-- ============================================================================
-- 
-- 카카오 웹툰 API에서 제공하는 추가 필드를 수집하기 위해 스키마 확장
-- 
-- 실행 방법:
--   bq query --use_legacy_sql=false < 이 파일
--
-- ============================================================================

-- 새 컬럼 추가
ALTER TABLE `kakao-webtoon-collector.kakao_webtoon.dim_webtoon`
ADD COLUMN IF NOT EXISTS seo_id STRING,
ADD COLUMN IF NOT EXISTS adult BOOLEAN,
ADD COLUMN IF NOT EXISTS catchphrase STRING,
ADD COLUMN IF NOT EXISTS badges ARRAY<STRING>,
ADD COLUMN IF NOT EXISTS content_id INT64;

-- 컬럼 설명 추가
ALTER TABLE `kakao-webtoon-collector.kakao_webtoon.dim_webtoon`
ALTER COLUMN seo_id SET OPTIONS(description="SEO ID (content.seoId)"),
ALTER COLUMN adult SET OPTIONS(description="성인 여부 (content.adult)"),
ALTER COLUMN catchphrase SET OPTIONS(description="캐치프레이즈 (content.catchphraseTwoLines)"),
ALTER COLUMN badges SET OPTIONS(description="배지 리스트 (content.badges의 title)"),
ALTER COLUMN content_id SET OPTIONS(description="콘텐츠 숫자 ID (content.id)");

