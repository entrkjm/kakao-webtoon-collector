#!/bin/bash
# weekday_rank 검증 스크립트

set -e

PROJECT_ID="kakao-webtoon-collector"
DATASET_ID="kakao_webtoon"

echo "=== weekday_rank 검증 ==="
echo ""

# 1. 각 요일별 weekday_rank 범위 확인
echo "1. 각 요일별 weekday_rank 범위 확인:"
bq query --use_legacy_sql=false --format=prettyjson "
SELECT 
  chart_date,
  weekday,
  sort_key,
  COUNT(*) AS total_webtoons,
  MIN(weekday_rank) AS min_weekday_rank,
  MAX(weekday_rank) AS max_weekday_rank,
  COUNT(DISTINCT weekday_rank) AS unique_ranks
FROM 
  \`${PROJECT_ID}.${DATASET_ID}.fact_weekly_chart\`
WHERE 
  chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY 
  chart_date, weekday, sort_key
ORDER BY 
  chart_date DESC, weekday, sort_key
" 2>&1 | grep -v "Waiting on"

echo ""
echo "---"
echo ""

# 2. 각 요일별 1위 웹툰 확인
echo "2. 각 요일별 1위 웹툰 (최신 수집 날짜):"
bq query --use_legacy_sql=false --format=prettyjson "
SELECT 
  chart_date,
  weekday,
  sort_key,
  weekday_rank,
  rank AS global_rank,
  d.title,
  d.author
FROM 
  \`${PROJECT_ID}.${DATASET_ID}.fact_weekly_chart\` f
JOIN 
  \`${PROJECT_ID}.${DATASET_ID}.dim_webtoon\` d
ON 
  f.webtoon_id = d.webtoon_id
WHERE 
  chart_date = (SELECT MAX(chart_date) FROM \`${PROJECT_ID}.${DATASET_ID}.fact_weekly_chart\`)
  AND sort_key = 'popularity'
  AND weekday_rank = 1
ORDER BY 
  weekday
" 2>&1 | grep -v "Waiting on"

echo ""
echo "---"
echo ""

# 3. 월요일 상위 10개
echo "3. 월요일 상위 10개 웹툰 (weekday_rank 기준):"
bq query --use_legacy_sql=false --format=prettyjson "
SELECT 
  weekday_rank,
  rank AS global_rank,
  d.title,
  d.author,
  f.view_count
FROM 
  \`${PROJECT_ID}.${DATASET_ID}.fact_weekly_chart\` f
JOIN 
  \`${PROJECT_ID}.${DATASET_ID}.dim_webtoon\` d
ON 
  f.webtoon_id = d.webtoon_id
WHERE 
  chart_date = (SELECT MAX(chart_date) FROM \`${PROJECT_ID}.${DATASET_ID}.fact_weekly_chart\`)
  AND weekday = 'mon'
  AND sort_key = 'popularity'
  AND weekday_rank IS NOT NULL
ORDER BY 
  weekday_rank
LIMIT 10
" 2>&1 | grep -v "Waiting on"

echo ""
echo "---"
echo ""

# 4. 금요일 상위 10개
echo "4. 금요일 상위 10개 웹툰 (weekday_rank 기준):"
bq query --use_legacy_sql=false --format=prettyjson "
SELECT 
  weekday_rank,
  rank AS global_rank,
  d.title,
  d.author,
  f.view_count
FROM 
  \`${PROJECT_ID}.${DATASET_ID}.fact_weekly_chart\` f
JOIN 
  \`${PROJECT_ID}.${DATASET_ID}.dim_webtoon\` d
ON 
  f.webtoon_id = d.webtoon_id
WHERE 
  chart_date = (SELECT MAX(chart_date) FROM \`${PROJECT_ID}.${DATASET_ID}.fact_weekly_chart\`)
  AND weekday = 'fri'
  AND sort_key = 'popularity'
  AND weekday_rank IS NOT NULL
ORDER BY 
  weekday_rank
LIMIT 10
" 2>&1 | grep -v "Waiting on"

echo ""
echo "✅ 검증 완료"
echo ""
echo "💡 카카오 웹툰 사이트에서 확인:"
echo "   https://webtoon.kakao.com"
echo "   - 각 요일 탭을 클릭하여 순위 확인"
echo "   - weekday_rank가 사이트의 순위와 일치하는지 확인"
