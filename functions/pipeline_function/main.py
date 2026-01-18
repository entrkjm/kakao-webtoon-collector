"""
Cloud Functions 진입점: 카카오 웹툰 주간 차트 수집 파이프라인

이 함수는 HTTP 트리거로 실행되며, 전체 ELT 파이프라인을 실행합니다.
- Extract: 카카오 웹툰 API에서 데이터 수집
- Load Raw: GCS에 JSON 원본 저장
- Transform: 데이터 파싱 및 정규화
- Load Refined: BigQuery에 정제된 데이터 저장
"""

import json
import logging
import os
from datetime import date
from typing import Optional

import functions_framework

# 프로젝트 루트를 Python 경로에 추가
import sys
from pathlib import Path

# Cloud Functions에서는 /workspace가 루트
# 로컬 테스트 시에는 상대 경로 사용
if os.path.exists('/workspace'):
    project_root = Path('/workspace')
    sys.path.insert(0, str(project_root))
else:
    # 로컬 테스트용: functions/pipeline_function에서 src로 접근
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # src 디렉토리도 경로에 추가
    src_path = project_root / 'src'
    if src_path.exists():
        sys.path.insert(0, str(src_path))

from src.extract import extract_webtoon_chart, try_api_endpoints, SORT_OPTIONS
from src.parse import parse_html_file
from src.parse_api import parse_api_response
from src.transform import transform_and_save
from src.utils import setup_logging, get_chart_jsonl_path, get_dim_webtoon_jsonl_path

# 로깅 설정 (먼저 설정)
setup_logging()
logger = logging.getLogger(__name__)

# GCS/BigQuery 업로드는 선택적으로 import (로컬 테스트 시 없을 수 있음)
try:
    from src.upload_gcs import upload_chart_data_to_gcs
    UPLOAD_GCS_AVAILABLE = True
except ImportError:
    UPLOAD_GCS_AVAILABLE = False
    logger.warning("GCS 업로드 모듈을 사용할 수 없습니다. (로컬 테스트 모드)")

try:
    from src.upload_bigquery import (
        upload_dim_webtoon,
        upload_fact_weekly_chart,
        get_bigquery_client,
    )
    UPLOAD_BIGQUERY_AVAILABLE = True
except ImportError:
    UPLOAD_BIGQUERY_AVAILABLE = False
    logger.warning("BigQuery 업로드 모듈을 사용할 수 없습니다. (로컬 테스트 모드)")

# 환경 변수
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'kakao-webtoon-raw')
BIGQUERY_PROJECT_ID = os.getenv('BIGQUERY_PROJECT_ID', 'kakao-webtoon-collector')
BIGQUERY_DATASET_ID = os.getenv('BIGQUERY_DATASET_ID', 'kakao_webtoon')

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

# GCS/BigQuery 업로드 모듈 import 전에 logger 설정 필요
# (위에서 이미 설정됨)


@functions_framework.http
def main(request):
    """
    Cloud Functions HTTP 트리거 진입점
    
    Args:
        request: Flask Request 객체
    
    Returns:
        HTTP 응답 (JSON)
    """
    try:
        # 요청 본문 파싱
        request_json = request.get_json(silent=True)
        if request_json is None:
            request_json = {}
        
        # 파라미터 추출
        chart_date_str = request_json.get('date')
        if chart_date_str:
            try:
                chart_date = date.fromisoformat(chart_date_str)
            except ValueError:
                logger.error(f"잘못된 날짜 형식: {chart_date_str}")
                return {'error': f'Invalid date format: {chart_date_str}'}, 400
        else:
            chart_date = date.today()
        
        sort_keys = request_json.get('sort_keys', ['popularity'])  # 기본값: 전체 인기순
        collect_all_weekdays = request_json.get('collect_all_weekdays', False)
        limit = request_json.get('limit')  # 테스트용 제한
        
        # 실행 날짜의 요일 계산 (0=월요일, 6=일요일)
        weekday_index = chart_date.weekday()  # 0=Monday, 6=Sunday
        weekday_map = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        current_weekday = weekday_map[weekday_index]
        
        logger.info(f"파이프라인 실행 시작: date={chart_date}, weekday={current_weekday}, sort_keys={sort_keys}, collect_all_weekdays={collect_all_weekdays}")
        
        all_success = True
        
        # API를 한 번만 호출하여 모든 데이터 수집
        logger.info("API 호출하여 기본 데이터 수집...")
        logger.info(f"⚠️  주의: 카카오 웹툰 API는 과거 날짜의 차트 데이터를 제공하지 않습니다. "
                   f"요청한 날짜({chart_date})와 무관하게 항상 현재 시점의 데이터를 수집합니다.")
        
        # collect_all_weekdays가 True이면 모든 요일 수집, False이면 현재 요일만 수집
        if collect_all_weekdays:
            api_data = try_api_endpoints(
                weekday=None,  # 모든 요일 수집 모드
                filter_type='전체',  # 전체 필터
                collect_all_weekdays=True,
                sort_key=None,  # 정렬은 클라이언트 사이드에서 처리
                chart_date=chart_date  # 메타데이터용 (API 호출에는 영향 없음)
            )
        else:
            # 현재 요일만 수집 (매일 수집 모드)
            api_data = try_api_endpoints(
                weekday=current_weekday,  # 현재 요일만 수집
                filter_type='전체',  # 전체 필터
                collect_all_weekdays=False,
                sort_key=None,  # 정렬은 클라이언트 사이드에서 처리
                chart_date=chart_date  # 메타데이터용 (API 호출에는 영향 없음)
            )
        
        if api_data is None:
            logger.error("데이터 수집 실패")
            return {'error': 'Failed to collect data'}, 500
        
        # Step 1: Load Raw (GCS에 JSON 원본 저장)
        if UPLOAD_GCS_AVAILABLE:
            logger.info("GCS에 원본 데이터 저장 중...")
            from tempfile import NamedTemporaryFile
            
            with NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_file:
                json.dump(api_data, tmp_file, ensure_ascii=False, indent=2)
                tmp_path = Path(tmp_file.name)
            
            try:
                # 기본 JSON 저장 (sort_key 없이)
                gcs_success = upload_chart_data_to_gcs(
                    chart_date,
                    sort_key=None,
                    json_file_path=tmp_path,
                    dry_run=False
                )
                if not gcs_success:
                    logger.warning("GCS 업로드 실패, 계속 진행...")
            finally:
                # 임시 파일 삭제
                if tmp_path.exists():
                    tmp_path.unlink()
        else:
            logger.info("GCS 업로드 모듈이 없습니다. 로컬 테스트 모드로 진행합니다.")
        
        # Step 2 & 3: Parse & Transform & Load Refined (각 정렬 옵션별로 처리)
        # 주의: parse_api_response는 각 sort_key별로 호출되므로 여기서는 호출하지 않음
        # 임시 디렉토리 사용 (Cloud Functions의 /tmp 사용)
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / 'kakao_webtoon_pipeline'
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 환경 변수 설정 (로컬 파일 저장 경로)
        os.environ['DATA_DIR'] = str(temp_dir)
        
        # 각 정렬 옵션별로 처리
        for sort_key in sort_keys:
            if sort_key not in SORT_OPTIONS:
                logger.warning(f"알 수 없는 정렬 키: {sort_key}, 건너뜁니다.")
                continue
            
            sort_name = SORT_OPTIONS[sort_key]
            logger.info(f"\n{'='*60}")
            logger.info(f"정렬 옵션: {sort_name} ({sort_key})")
            logger.info(f"{'='*60}")
            
            try:
                # API 데이터에 정렬 키 추가
                api_data_with_sort = api_data.copy()
                api_data_with_sort['_sort_key'] = sort_key
                
                # 정렬된 데이터 파싱 (parse_api_response가 sort_key를 받아서 정렬함)
                sorted_parsed_data = parse_api_response(api_data_with_sort, sort_key=sort_key)
                
                if len(sorted_parsed_data) == 0:
                    logger.warning(f"정렬된 데이터가 없습니다 ({sort_name})")
                    continue
                
                # 정렬 정보 추가
                for item in sorted_parsed_data:
                    item['_sort_key'] = sort_key
                    item['_sort_name'] = sort_name
                
                # 데이터 변환 및 저장
                logger.info(f"데이터 변환 및 저장 시작 ({sort_name})...")
                success = transform_and_save(sorted_parsed_data, chart_date, sort_key)
                
                if success:
                    # 저장된 JSONL 파일을 BigQuery에 업로드
                    if UPLOAD_BIGQUERY_AVAILABLE:
                        from src.utils import get_dim_webtoon_jsonl_path, get_chart_jsonl_path
                        
                        # dim_webtoon 업로드 (첫 번째 정렬 옵션일 때만)
                        if sort_key == sort_keys[0]:
                            dim_jsonl_path = get_dim_webtoon_jsonl_path()
                            if dim_jsonl_path.exists():
                                logger.info(f"dim_webtoon.jsonl 파일 발견, BigQuery 업로드 시작: {dim_jsonl_path}")
                                try:
                                    upload_success = upload_dim_webtoon(jsonl_path=dim_jsonl_path, dry_run=False)
                                    if upload_success:
                                        logger.info("✅ dim_webtoon BigQuery 업로드 성공")
                                    else:
                                        logger.error("dim_webtoon BigQuery 업로드 실패")
                                except Exception as e:
                                    logger.error(f"dim_webtoon BigQuery 업로드 중 오류 발생: {e}")
                                    import traceback
                                    traceback.print_exc()
                        
                        # fact_weekly_chart 업로드
                        fact_jsonl_path = get_chart_jsonl_path(chart_date, sort_key)
                        if fact_jsonl_path.exists():
                            logger.info(f"fact_weekly_chart.jsonl 파일 발견, BigQuery 업로드 시작: {fact_jsonl_path}")
                            try:
                                upload_success = upload_fact_weekly_chart(
                                    chart_date=chart_date,
                                    sort_key=sort_key,
                                    jsonl_path=fact_jsonl_path,
                                    dry_run=False
                                )
                                if upload_success:
                                    logger.info(f"✅ fact_weekly_chart BigQuery 업로드 성공 ({sort_name})")
                                else:
                                    logger.error(f"fact_weekly_chart BigQuery 업로드 실패 ({sort_name})")
                            except Exception as e:
                                logger.error(f"fact_weekly_chart BigQuery 업로드 중 오류 발생 ({sort_name}): {e}")
                                import traceback
                                traceback.print_exc()
                        else:
                            logger.warning(f"fact_weekly_chart.jsonl 파일이 존재하지 않습니다: {fact_jsonl_path}")
                    else:
                        logger.info("BigQuery 업로드 모듈이 없습니다. 로컬 테스트 모드로 진행합니다.")
                    
                    # 정렬별 GCS 업로드
                    if UPLOAD_GCS_AVAILABLE:
                        logger.info(f"정렬별 GCS 업로드 시작 ({sort_name})...")
                        # 정렬된 데이터를 임시 파일에 저장
                        from tempfile import NamedTemporaryFile
                        with NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_file:
                            # 정렬된 API 데이터 재구성
                            sorted_api_data = api_data.copy()
                            sorted_api_data['_sort_key'] = sort_key
                            json.dump(sorted_api_data, tmp_file, ensure_ascii=False, indent=2)
                            tmp_path = Path(tmp_file.name)
                        
                        try:
                            gcs_success = upload_chart_data_to_gcs(
                                chart_date,
                                sort_key=sort_key,
                                json_file_path=tmp_path,
                                dry_run=False
                            )
                            if gcs_success:
                                logger.info(f"✅ GCS 업로드 완료 ({sort_name})")
                            else:
                                logger.warning(f"GCS 업로드 실패 ({sort_name}), 계속 진행...")
                        finally:
                            if tmp_path.exists():
                                tmp_path.unlink()
                    
                    logger.info(f"✅ 정렬 옵션 '{sort_name}' 수집 완료!")
                else:
                    logger.error(f"데이터 변환 및 저장 실패 ({sort_name})")
                    all_success = False
                    continue
                    
            except Exception as e:
                logger.error(f"정렬 옵션 '{sort_name}' 처리 중 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                all_success = False
        
        if all_success:
            logger.info("🎉 파이프라인 실행 완료!")
            return {'status': 'success', 'date': str(chart_date)}, 200
        else:
            logger.error("❌ 파이프라인 실행 중 일부 오류 발생")
            return {'status': 'partial_failure', 'date': str(chart_date)}, 500
            
    except Exception as e:
        logger.error(f"파이프라인 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500

