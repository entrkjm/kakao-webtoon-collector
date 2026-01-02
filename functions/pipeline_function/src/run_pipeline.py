"""
파이프라인 통합 실행 스크립트

Extract → Parse → Transform 전체 플로우를 실행합니다.
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.extract import extract_webtoon_chart, SORT_OPTIONS
from src.parse import parse_html_file
from src.transform import transform_and_save
from src.utils import setup_logging, get_log_file_path

# Selenium 기반 정렬 수집 시도
try:
    from src.extract_with_sort import extract_webtoon_chart_with_sort, SELENIUM_AVAILABLE
except ImportError:
    SELENIUM_AVAILABLE = False
    extract_webtoon_chart_with_sort = None

logger = None


def run_pipeline(chart_date: date = None, html_file: Path = None, collect_all_weekdays: bool = False, sort_keys: list = None) -> bool:
    """
    전체 파이프라인을 실행합니다.
    
    Args:
        chart_date: 수집 날짜 (None이면 오늘 날짜)
        html_file: 이미 수집된 HTML 파일 경로 (None이면 새로 수집)
        collect_all_weekdays: True이면 모든 요일 데이터 수집
        sort_keys: 정렬 키 리스트 (None이면 ['popularity']만 수집)
    
    Returns:
        성공 여부
    """
    global logger
    # 로그 파일 경로 생성
    log_file = get_log_file_path("pipeline")
    setup_logging(log_file=log_file)
    logger = logging.getLogger(__name__)
    logger.info(f"로그 파일: {log_file}")
    
    if chart_date is None:
        chart_date = date.today()
    
    # 정렬 키 기본값 설정
    if sort_keys is None:
        sort_keys = ['popularity']  # 기본값: 전체 인기순만
    
    try:
        all_success = True
        
        # API를 한 번만 호출하여 모든 데이터 수집
        # (각 정렬 옵션마다 API를 호출하는 대신, 한 번 호출 후 클라이언트 사이드에서 정렬)
        logger.info("API 호출하여 기본 데이터 수집...")
        html_path = None
        if not html_file:
            html_path = extract_webtoon_chart(chart_date, collect_all_weekdays=collect_all_weekdays)
            if html_path is None:
                logger.error("HTML 수집 실패")
                return False
        
        # 각 정렬 옵션별로 파싱 및 저장
        for sort_key in sort_keys:
            if sort_key not in SORT_OPTIONS:
                logger.warning(f"알 수 없는 정렬 키: {sort_key}, 건너뜁니다.")
                continue
            
            sort_name = SORT_OPTIONS[sort_key]
            logger.info(f"\n{'='*60}")
            logger.info(f"정렬 옵션: {sort_name} ({sort_key})")
            logger.info(f"{'='*60}")
            
            # Step 1: Extract (HTML 수집)
            # 이미 수집된 HTML 파일 사용 (각 정렬 옵션마다 재호출하지 않음)
            if html_file:
                logger.info(f"기존 HTML 파일 사용: {html_file}")
                current_html_path = html_file
            else:
                current_html_path = html_path
                if current_html_path is None:
                    logger.error(f"HTML 파일이 없습니다 ({sort_name})")
                    all_success = False
                    continue
            
            # Step 2: Parse (HTML 파싱)
            # 정렬 키를 전달하여 클라이언트 사이드에서 정렬
            logger.info(f"HTML 파싱 시작 ({sort_name})...")
            
            # HTML 파일을 읽어서 API 데이터에 정렬 키 추가
            import json
            import re
            html_content = current_html_path.read_text(encoding='utf-8')
            
            # API 데이터에 정렬 키 추가
            json_match = re.search(r'<script[^>]*id=[\'"]webtoon-data[\'"][^>]*>(.*?)</script>', html_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                api_data = json.loads(json_str)
                api_data['_sort_key'] = sort_key
                
                # 수정된 API 데이터로 임시 HTML 생성
                from pathlib import Path
                import tempfile
                temp_html = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
                temp_html.write(f"<!-- Sort: {sort_name} -->\n<script type='application/json' id='webtoon-data'>{json.dumps(api_data, ensure_ascii=False)}</script>")
                temp_html.close()
                temp_html_path = Path(temp_html.name)
            else:
                temp_html_path = current_html_path
            
            parsed_data = parse_html_file(temp_html_path)
            
            # 임시 파일 삭제
            if temp_html_path != current_html_path and temp_html_path.exists():
                temp_html_path.unlink()
            if len(parsed_data) == 0:
                logger.error(f"파싱된 데이터가 없습니다 ({sort_name}). HTML 구조를 확인하세요.")
                all_success = False
                continue
            
            logger.info(f"파싱 완료 ({sort_name}): {len(parsed_data)}개 웹툰 데이터")
            
            # Step 3: Transform (데이터 변환 및 저장)
            # 정렬 정보를 메타데이터로 추가
            for item in parsed_data:
                item['_sort_key'] = sort_key
                item['_sort_name'] = sort_name
            
            logger.info(f"데이터 변환 및 저장 시작 ({sort_name})...")
            success = transform_and_save(parsed_data, chart_date)
            
            if success:
                logger.info(f"✅ {sort_name} 수집 완료!")
                
                # Step 4: GCS 업로드 (선택적, 환경 변수로 제어)
                import os
                if os.getenv('UPLOAD_TO_GCS', 'false').lower() == 'true':
                    logger.info(f"GCS 업로드 시작 ({sort_name})...")
                    from src.upload_gcs import upload_chart_data_to_gcs
                    gcs_success = upload_chart_data_to_gcs(chart_date, sort_key=sort_key)
                    if gcs_success:
                        logger.info(f"✅ GCS 업로드 완료 ({sort_name})")
                    else:
                        logger.warning(f"⚠️ GCS 업로드 실패 ({sort_name}), 계속 진행...")
                
                # Step 5: BigQuery 업로드 (선택적, 환경 변수로 제어)
                if os.getenv('UPLOAD_TO_BIGQUERY', 'false').lower() == 'true':
                    logger.info(f"BigQuery 업로드 시작 ({sort_name})...")
                    from src.upload_bigquery import upload_dim_webtoon, upload_fact_weekly_chart
                    
                    # dim_webtoon 업로드 (한 번만)
                    if sort_key == sort_keys[0]:  # 첫 번째 정렬 옵션일 때만
                        dim_success = upload_dim_webtoon()
                        if dim_success:
                            logger.info("✅ dim_webtoon 업로드 완료")
                        else:
                            logger.warning("⚠️ dim_webtoon 업로드 실패, 계속 진행...")
                    
                    # fact_weekly_chart 업로드
                    fact_success = upload_fact_weekly_chart(chart_date, sort_key=sort_key)
                    if fact_success:
                        logger.info(f"✅ fact_weekly_chart 업로드 완료 ({sort_name})")
                    else:
                        logger.warning(f"⚠️ fact_weekly_chart 업로드 실패 ({sort_name}), 계속 진행...")
                
                # Step 4: GCS 업로드 (선택적, 환경 변수로 제어)
                if os.getenv('UPLOAD_TO_GCS', 'false').lower() == 'true':
                    logger.info(f"GCS 업로드 시작 ({sort_name})...")
                    from src.upload_gcs import upload_chart_data_to_gcs
                    gcs_success = upload_chart_data_to_gcs(chart_date, sort_key=sort_key)
                    if gcs_success:
                        logger.info(f"✅ GCS 업로드 완료 ({sort_name})")
                    else:
                        logger.warning(f"⚠️ GCS 업로드 실패 ({sort_name}), 계속 진행...")
                
                # Step 5: BigQuery 업로드 (선택적, 환경 변수로 제어)
                if os.getenv('UPLOAD_TO_BIGQUERY', 'false').lower() == 'true':
                    logger.info(f"BigQuery 업로드 시작 ({sort_name})...")
                    from src.upload_bigquery import upload_dim_webtoon, upload_fact_weekly_chart
                    
                    # dim_webtoon 업로드 (한 번만)
                    if sort_key == sort_keys[0]:  # 첫 번째 정렬 옵션일 때만
                        dim_success = upload_dim_webtoon()
                        if dim_success:
                            logger.info("✅ dim_webtoon 업로드 완료")
                        else:
                            logger.warning("⚠️ dim_webtoon 업로드 실패, 계속 진행...")
                    
                    # fact_weekly_chart 업로드
                    fact_success = upload_fact_weekly_chart(chart_date, sort_key=sort_key)
                    if fact_success:
                        logger.info(f"✅ fact_weekly_chart 업로드 완료 ({sort_name})")
                    else:
                        logger.warning(f"⚠️ fact_weekly_chart 업로드 실패 ({sort_name}), 계속 진행...")
            else:
                logger.error(f"❌ {sort_name} 데이터 변환 및 저장 실패")
                all_success = False
        
        if all_success:
            logger.info(f"\n✅ 모든 정렬 옵션 수집 완료!")
            return True
        else:
            logger.error(f"\n❌ 일부 정렬 옵션 수집 실패")
            return False
            
    except Exception as e:
        logger.error(f"파이프라인 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='카카오 웹툰 주간 차트 수집 파이프라인')
    parser.add_argument(
        '--date',
        type=str,
        help='수집 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)'
    )
    parser.add_argument(
        '--html',
        type=str,
        help='이미 수집된 HTML 파일 경로 (지정 시 새로 수집하지 않음)'
    )
    parser.add_argument(
        '--all-weekdays',
        action='store_true',
        help='모든 요일 데이터 수집 (기본값: 월요일만)'
    )
    parser.add_argument(
        '--sort-keys',
        type=str,
        nargs='+',
        help='정렬 키 리스트 (popularity, views, createdAt, popularityMale, popularityFemale). 기본값: popularity만'
    )
    parser.add_argument(
        '--all-sorts',
        action='store_true',
        help='모든 정렬 옵션 수집 (popularity, views, createdAt, popularityMale, popularityFemale)'
    )
    
    args = parser.parse_args()
    
    # 날짜 파싱
    chart_date = None
    if args.date:
        try:
            chart_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"잘못된 날짜 형식: {args.date} (YYYY-MM-DD 형식 사용)")
            sys.exit(1)
    
    # HTML 파일 경로
    html_file = None
    if args.html:
        html_file = Path(args.html)
        if not html_file.exists():
            print(f"HTML 파일을 찾을 수 없습니다: {html_file}")
            sys.exit(1)
    
    # 정렬 키 설정
    sort_keys = None
    if args.all_sorts:
        sort_keys = list(SORT_OPTIONS.keys())
        print(f"모든 정렬 옵션 수집: {sort_keys}")
    elif args.sort_keys:
        sort_keys = args.sort_keys
        print(f"지정된 정렬 옵션 수집: {sort_keys}")
    
    # 파이프라인 실행
    success = run_pipeline(
        chart_date=chart_date,
        html_file=html_file,
        collect_all_weekdays=args.all_weekdays,
        sort_keys=sort_keys
    )
    sys.exit(0 if success else 1)

