#!/bin/bash
# 카카오 웹툰 GCS 원본 데이터 정리 스크립트
#
# 목적: 잘못된 데이터 수집 시 생성된 GCS 원본 파일 삭제
#
# 주의: 이 스크립트는 특정 날짜 범위의 GCS 파일을 삭제합니다.

set -e

BUCKET_NAME="kakao-webtoon-raw"
PREFIX="raw/"

echo "=========================================="
echo "카카오 웹툰 GCS 원본 데이터 정리"
echo "=========================================="
echo ""
echo "버킷: gs://${BUCKET_NAME}"
echo "경로: ${PREFIX}"
echo ""

# 현재 파일 목록 확인
echo "=== 현재 GCS 파일 목록 ==="
gsutil ls -r "gs://${BUCKET_NAME}/${PREFIX}" 2>&1 | head -20 || echo "파일이 없거나 접근 권한이 없습니다."

echo ""
read -p "모든 원본 파일을 삭제하시겠습니까? (yes 입력): " confirm

if [ "$confirm" != "yes" ]; then
    echo "취소되었습니다."
    exit 1
fi

echo ""
echo "=== GCS 파일 삭제 중 ==="
gsutil -m rm -r "gs://${BUCKET_NAME}/${PREFIX}**" 2>&1 || echo "파일이 없거나 이미 삭제되었습니다."

echo ""
echo "✅ GCS 원본 파일 삭제 완료"
echo ""

# 삭제 확인
echo "=== 삭제 확인 ==="
gsutil ls "gs://${BUCKET_NAME}/${PREFIX}" 2>&1 | head -5 || echo "파일이 없습니다."

echo ""
echo "=========================================="
echo "GCS 원본 데이터 정리 완료"
echo "=========================================="
