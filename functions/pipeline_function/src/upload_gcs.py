"""
GCS 업로드 모듈

로컬에 저장된 HTML/JSON 원본 파일을 GCS에 업로드하는 기능을 제공합니다.
- 차트 데이터 업로드 (API 응답 JSON)
"""

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional

from google.cloud import storage
from google.cloud.exceptions import NotFound

from src.utils import get_raw_html_dir, setup_logging

logger = logging.getLogger(__name__)


# GCS 설정 (환경 변수 또는 기본값)
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'kakao-webtoon-raw')
GCS_PROJECT_ID = os.getenv('GCS_PROJECT_ID', 'kakao-webtoon-collector')


def get_gcs_client() -> storage.Client:
    """
    GCS 클라이언트를 생성합니다.
    
    Returns:
        GCS 클라이언트 객체
    """
    return storage.Client(project=GCS_PROJECT_ID)


def upload_file_to_gcs(
    local_file_path: Path,
    gcs_path: str,
    content_type: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """
    로컬 파일을 GCS에 업로드합니다.
    
    Args:
        local_file_path: 로컬 파일 경로
        gcs_path: GCS 경로 (예: "raw_html/2026-01-01/webtoon_chart.json")
        content_type: Content-Type (None이면 파일 확장자로 자동 판단)
        dry_run: True이면 실제 업로드하지 않고 검증만 수행
    
    Returns:
        성공 여부
    """
    if not local_file_path.exists():
        logger.warning(f"파일이 존재하지 않습니다: {local_file_path}")
        return False
    
    if dry_run:
        logger.info(f"[DRY RUN] GCS 업로드 예정: {local_file_path} -> gs://{GCS_BUCKET_NAME}/{gcs_path}")
        return True
    
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        
        # Content-Type 자동 판단
        if content_type is None:
            if local_file_path.suffix == '.json':
                content_type = 'application/json'
            elif local_file_path.suffix == '.html':
                content_type = 'text/html'
            else:
                content_type = 'application/octet-stream'
        
        # 파일 업로드
        blob.upload_from_filename(str(local_file_path), content_type=content_type)
        
        logger.info(f"✅ GCS 업로드 완료: gs://{GCS_BUCKET_NAME}/{gcs_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ GCS 업로드 실패: {local_file_path} -> gs://{GCS_BUCKET_NAME}/{gcs_path}, 오류: {e}")
        return False


def upload_chart_data_to_gcs(
    chart_date: date,
    sort_key: Optional[str] = None,
    json_file_path: Optional[Path] = None,
    dry_run: bool = False
) -> bool:
    """
    차트 데이터(API 응답 JSON)를 GCS에 업로드합니다.
    
    Args:
        chart_date: 차트 날짜
        sort_key: 정렬 키 ("popularity", "views", "createdAt", "popularityMale", "popularityFemale")
        json_file_path: JSON 파일 경로 (None이면 기본 경로에서 찾기)
        dry_run: True이면 실제 업로드하지 않고 검증만 수행
    
    Returns:
        성공 여부
    """
    # 파일 경로 찾기
    if json_file_path is None:
        raw_dir = get_raw_html_dir(chart_date)
        if sort_key:
            json_file_path = raw_dir / f"webtoon_chart_{sort_key}.json"
        else:
            json_file_path = raw_dir / "webtoon_chart.json"
    
    if not json_file_path.exists():
        logger.warning(f"차트 데이터 파일이 없습니다: {json_file_path}")
        return False
    
    # GCS 경로 생성
    date_str = chart_date.strftime('%Y-%m-%d')
    if sort_key:
        gcs_path = f"raw_html/{date_str}/sort_{sort_key}/webtoon_chart.json"
    else:
        gcs_path = f"raw_html/{date_str}/webtoon_chart.json"
    
    return upload_file_to_gcs(json_file_path, gcs_path, content_type='application/json', dry_run=dry_run)


def upload_all_chart_data_for_date(
    chart_date: date,
    sort_keys: Optional[list] = None,
    dry_run: bool = False
) -> bool:
    """
    특정 날짜의 모든 차트 데이터를 GCS에 업로드합니다.
    
    Args:
        chart_date: 차트 날짜
        sort_keys: 정렬 키 리스트 (None이면 모든 정렬 옵션 시도)
        dry_run: True이면 실제 업로드하지 않고 검증만 수행
    
    Returns:
        성공 여부 (모든 파일 업로드 성공 시 True)
    """
    from src.extract import SORT_OPTIONS
    
    if sort_keys is None:
        sort_keys = list(SORT_OPTIONS.keys())
    
    all_success = True
    for sort_key in sort_keys:
        success = upload_chart_data_to_gcs(chart_date, sort_key=sort_key, dry_run=dry_run)
        if not success:
            all_success = False
    
    return all_success

