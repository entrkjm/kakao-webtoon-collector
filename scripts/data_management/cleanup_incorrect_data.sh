#!/bin/bash
# 카카오 웹툰 잘못된 데이터 정리 스크립트
#
# 목적: 정렬 로직이 잘못되어 수집된 데이터를 삭제하고 재수집 준비
#
# 주의: 이 스크립트는 fact_weekly_chart 테이블의 모든 데이터를 삭제합니다.
#       dim_webtoon은 유지됩니다 (웹툰 마스터 정보는 유용).

set -e

PROJECT_ID="kakao-webtoon-collector"
DATASET_ID="kakao_webtoon"
TABLE_NAME="fact_weekly_chart"

echo "=========================================="
echo "카카오 웹툰 잘못된 데이터 정리"
echo "=========================================="
echo ""
echo "⚠️  주의: 이 스크립트는 fact_weekly_chart 테이블의 모든 데이터를 삭제합니다."
echo "   - dim_webtoon은 유지됩니다"
echo "   - GCS 원본 파일은 별도로 삭제해야 합니다"
echo ""

# 현재 데이터 현황 확인
echo "=== 현재 데이터 현황 ==="
bq query --use_legacy_sql=false --format=prettyjson "
SELECT 
  COUNT(*) AS total_records,
  COUNT(DISTINCT chart_date) AS unique_dates,
  MIN(chart_date) AS earliest_date,
  MAX(chart_date) AS latest_date
FROM 
  \`${PROJECT_ID}.${DATASET_ID}.${TABLE_NAME}\`
" 2>&1 | grep -v "Waiting on"

echo ""
read -p "정말 모든 fact_weekly_chart 데이터를 삭제하시겠습니까? (yes 입력): " confirm

if [ "$confirm" != "yes" ]; then
    echo "취소되었습니다."
    exit 1
fi

echo ""
echo "=== fact_weekly_chart 데이터 삭제 중 ==="

# 모든 파티션 삭제 (DELETE 쿼리 사용)
bq query --use_legacy_sql=false "
DELETE FROM \`${PROJECT_ID}.${DATASET_ID}.${TABLE_NAME}\`
WHERE TRUE
" 2>&1 | grep -v "Waiting on"

echo ""
echo "✅ fact_weekly_chart 데이터 삭제 완료"
echo ""

# 삭제 확인
echo "=== 삭제 확인 ==="
bq query --use_legacy_sql=false --format=prettyjson "
SELECT 
  COUNT(*) AS remaining_records
FROM 
  \`${PROJECT_ID}.${DATASET_ID}.${TABLE_NAME}\`
" 2>&1 | grep -v "Waiting on"

echo ""
echo "=========================================="
echo "다음 단계:"
echo "1. 정렬 로직 수정 (views reverse=False)"
echo "2. 데이터 재수집 실행"
echo "3. 재수집된 데이터 검증"
echo "=========================================="
