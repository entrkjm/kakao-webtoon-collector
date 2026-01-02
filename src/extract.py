"""
Extract 모듈: 카카오 웹툰 페이지 HTML 수집

이 모듈은 카카오 웹툰 주간 차트 페이지의 HTML을 수집하여
로컬 파일 시스템에 저장합니다 (GCS 대체).

주의: 
1. 먼저 API 엔드포인트를 찾아서 requests로 직접 호출 시도
2. API를 찾을 수 없으면 모바일 버전 HTML 수집 시도
3. 그래도 안 되면 Selenium 사용 (Cloud Functions에서는 비권장)
"""

import logging
import time
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils import get_raw_html_dir, setup_logging

logger = logging.getLogger(__name__)

# 카카오 웹툰 주간 차트 URL
KAKAO_WEBTOON_CHART_URL = "https://webtoon.kakao.com"
KAKAO_WEBTOON_MOBILE_URL = "https://m.webtoon.kakao.com"

# API 엔드포인트
KAKAO_WEBTOON_API_BASE = "https://gateway-kw.kakao.com/section/v2/timetables/days"

# 요일 매핑
WEEKDAY_MAPPING = {
    '월': 'mon',
    '화': 'tue',
    '수': 'wed',
    '목': 'thu',
    '금': 'fri',
    '토': 'sat',
    '일': 'sun'
}

# 필터 매핑
FILTER_MAPPING = {
    '전체': '',
    '연재무료': '_free_publishing',
    '기다무': '_wait_free'
}

# 정렬 옵션 매핑 (__NEXT_DATA__에서 확인한 정렬 키)
SORT_OPTIONS = {
    'popularity': '전체 인기순',  # 기본값
    'views': '조회순',
    'createdAt': '최신순',
    'popularityMale': '남성 인기순',
    'popularityFemale': '여성 인기순'
}


def create_session() -> requests.Session:
    """
    재시도 로직이 포함된 requests 세션을 생성합니다.
    브라우저 동작을 흉내내기 위해 필요한 헤더를 설정합니다.
    
    Returns:
        설정된 requests.Session 객체
    """
    session = requests.Session()
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://webtoon.kakao.com',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'DNT': '1',
    })
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def try_api_endpoints(weekday: Optional[str] = None, filter_type: Optional[str] = None, collect_all_weekdays: bool = False, sort_key: Optional[str] = None, chart_date: Optional[date] = None) -> Optional[dict]:
    """
    카카오 웹툰 API 엔드포인트를 호출하여 데이터를 가져옵니다.
    
    ⚠️ 중요: 카카오 웹툰 API는 과거 날짜의 차트 데이터를 제공하지 않습니다.
    chart_date 파라미터는 메타데이터로만 사용되며, 항상 현재 시점의 데이터를 수집합니다.
    
    Args:
        weekday: 요일 ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
                 None이면 모든 요일을 시도
        filter_type: 필터 타입 ('전체', '연재무료', '기다무')
                    None이면 '전체' 사용
        collect_all_weekdays: True이면 모든 요일 데이터를 합쳐서 반환
        sort_key: 정렬 키 ('popularity', 'views', 'createdAt', 'popularityMale', 'popularityFemale')
                 None이면 기본값 (popularity) 사용
        chart_date: 수집 날짜 (메타데이터용, API 호출에는 영향 없음)
    
    Returns:
        JSON 데이터 (실패 시 None)
        collect_all_weekdays=True인 경우 모든 요일 데이터를 합친 구조 반환
    """
    # 과거 날짜로 수집 시도 시 경고
    if chart_date and chart_date < date.today():
        logger.warning(
            f"⚠️  과거 날짜({chart_date})로 수집 시도했지만, "
            f"카카오 웹툰 API는 항상 현재 시점({date.today()})의 데이터만 제공합니다. "
            f"실제로는 현재 시점의 데이터가 수집됩니다."
        )
    session = create_session()
    
    # 기본값 설정
    if filter_type is None:
        filter_type = '전체'
    if sort_key is None:
        sort_key = 'popularity'  # 기본값: 전체 인기순
    
    # placement 파라미터 구성
    if weekday is None:
        # 모든 요일 시도
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    else:
        weekdays = [weekday]
    
    # 모든 요일 수집 모드
    if collect_all_weekdays and len(weekdays) > 1:
        all_data = []
        for wd in weekdays:
            placement = f"timetable_{wd}"
            if filter_type in FILTER_MAPPING:
                placement += FILTER_MAPPING[filter_type]
            
            url = f"{KAKAO_WEBTOON_API_BASE}?placement={placement}"
            
            logger.info(f"API 엔드포인트 호출: {url}")
            
            try:
                headers = {
                    'Referer': 'https://webtoon.kakao.com/',
                    'Origin': 'https://webtoon.kakao.com'
                }
                
                response = session.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # 각 요일 데이터에 메타데이터 추가
                if isinstance(data, dict) and 'data' in data:
                    for item in data.get('data', []):
                        if isinstance(item, dict):
                            item['_weekday'] = wd
                            item['_placement'] = placement
                            item['_filter_type'] = filter_type
                
                all_data.append(data)
                time.sleep(0.5)  # API 호출 간 딜레이
                
            except Exception as e:
                logger.warning(f"API 호출 실패 ({url}): {e}")
                continue
        
        if not all_data:
            logger.error("모든 요일 API 호출 실패")
            return None
        
        # 모든 요일 데이터를 합친 구조로 반환
        combined_data = {
            'data': [],
            '_collected_all_weekdays': True,
            '_filter_type': filter_type
        }
        
        for data in all_data:
            if isinstance(data, dict) and 'data' in data:
                combined_data['data'].extend(data['data'])
        
        logger.info(f"모든 요일 데이터 수집 완료: {len(combined_data['data'])}개 그룹")
        return combined_data
    
    # 단일 요일 또는 첫 번째 성공한 요일 반환
    for wd in weekdays:
        placement = f"timetable_{wd}"
        if filter_type in FILTER_MAPPING:
            placement += FILTER_MAPPING[filter_type]
        
        # URL 구성 (정렬 파라미터 추가 시도)
        url = f"{KAKAO_WEBTOON_API_BASE}?placement={placement}"
        
        # 정렬 파라미터 추가 (API가 지원하는 경우를 대비)
        params = {}
        if sort_key and sort_key in SORT_OPTIONS:
            # 여러 방식으로 시도 (API가 지원하는 방식 확인 필요)
            # 현재는 주석 처리 (API가 지원하지 않는 것으로 확인됨)
            # params['sort'] = sort_key
            # params['orderBy'] = sort_key
            pass
        
        logger.info(f"API 엔드포인트 시도: {url}")
        
        try:
            headers = {
                'Referer': 'https://webtoon.kakao.com/',
                'Origin': 'https://webtoon.kakao.com'
            }
            
            response = session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 응답에 메타데이터 추가
            if isinstance(data, dict):
                data['_placement'] = placement
                data['_weekday'] = wd
                data['_filter_type'] = filter_type
                data['_sort_key'] = sort_key
                data['_sort_name'] = SORT_OPTIONS.get(sort_key, '알 수 없음')
            
            logger.info(f"API 호출 성공: {url}")
            return data
            
        except Exception as e:
            logger.warning(f"API 호출 실패 ({url}): {e}")
            continue
    
    logger.error("모든 API 엔드포인트 시도 실패")
    return None


def fetch_webtoon_chart_html(url: Optional[str] = None, use_mobile: bool = True, chart_date: Optional[date] = None, collect_all_weekdays: bool = False, sort_key: Optional[str] = None) -> Optional[str]:
    """
    카카오 웹툰 주간 차트 페이지의 HTML을 수집합니다.
    
    우선순위:
    1. API 엔드포인트 시도
    2. 모바일 버전 HTML 수집
    3. 데스크톱 버전 HTML 수집
    
    Args:
        url: 웹툰 차트 URL (None이면 기본 URL 사용)
        use_mobile: 모바일 버전 사용 여부
        chart_date: 수집 날짜
        collect_all_weekdays: True이면 모든 요일 데이터 수집
        sort_key: 정렬 키 ('popularity', 'views', 'createdAt', 'popularityMale', 'popularityFemale')
    
    Returns:
        HTML 문자열 (실패 시 None)
    """
    # 1. API 엔드포인트 시도
    api_data = try_api_endpoints(collect_all_weekdays=collect_all_weekdays, sort_key=sort_key)
    if api_data:
        import json
        if chart_date is None:
            chart_date = date.today()
        json_path = save_json_to_file(api_data, chart_date)
        sort_info = f"<!-- API Response -->\n"
        html = f"{sort_info}<script type='application/json' id='webtoon-data'>{json.dumps(api_data, ensure_ascii=False)}</script>"
        return html
    
    # 2. HTML 수집
    if url is None:
        url = KAKAO_WEBTOON_MOBILE_URL if use_mobile else KAKAO_WEBTOON_CHART_URL
    
    logger.info(f"웹툰 차트 페이지 수집 시작: {url}")
    
    try:
        session = create_session()
        
        if use_mobile:
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
            })
        
        time.sleep(1)
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        html = response.text
        logger.info(f"HTML 수집 성공: {len(html)} bytes")
        return html
        
    except Exception as e:
        logger.error(f"HTML 수집 실패: {e}")
        return None


def save_json_to_file(json_data: dict, chart_date: date, filename: Optional[str] = None) -> Optional[Path]:
    """
    API 응답 JSON을 로컬 파일로 저장합니다.
    
    Args:
        json_data: 저장할 JSON 데이터
        chart_date: 수집 날짜
        filename: 저장할 파일명 (None이면 자동 생성)
    
    Returns:
        저장된 파일의 Path 객체 (실패 시 None)
    """
    save_dir = get_raw_html_dir(chart_date)
    
    if filename is None:
        filename = "webtoon_chart.json"
    
    file_path = save_dir / filename
    
    try:
        import json
        file_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(f"JSON 저장 완료: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"JSON 저장 실패: {file_path}, 오류: {e}")
        return None


def save_html_to_file(html: str, chart_date: date, filename: Optional[str] = None) -> Path:
    """
    수집한 HTML을 로컬 파일로 저장합니다.
    
    Args:
        html: 저장할 HTML 문자열
        chart_date: 수집 날짜
        filename: 저장할 파일명 (None이면 자동 생성)
    
    Returns:
        저장된 파일의 Path 객체
    """
    save_dir = get_raw_html_dir(chart_date)
    
    if filename is None:
        filename = "webtoon_chart.html"
    
    file_path = save_dir / filename
    
    try:
        file_path.write_text(html, encoding='utf-8')
        logger.info(f"HTML 저장 완료: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"HTML 저장 실패: {file_path}, 오류: {e}")
        raise


def extract_webtoon_chart(chart_date: Optional[date] = None, url: Optional[str] = None, use_mobile: bool = True, collect_all_weekdays: bool = False, sort_key: Optional[str] = None) -> Optional[Path]:
    """
    카카오 웹툰 주간 차트를 수집하여 로컬에 저장합니다.
    
    Args:
        chart_date: 수집 날짜 (None이면 오늘 날짜 사용)
        url: 웹툰 차트 URL (None이면 기본 URL 사용)
        use_mobile: 모바일 버전 사용 여부
        collect_all_weekdays: True이면 모든 요일 데이터 수집
        sort_key: 정렬 키 ('popularity', 'views', 'createdAt', 'popularityMale', 'popularityFemale')
    
    Returns:
        저장된 HTML 파일의 Path 객체 (실패 시 None)
    """
    if chart_date is None:
        chart_date = date.today()
    
    try:
        html = fetch_webtoon_chart_html(url, use_mobile=use_mobile, chart_date=chart_date, collect_all_weekdays=collect_all_weekdays, sort_key=sort_key)
        
        if html is None:
            logger.error("HTML 수집 실패")
            return None
        
        file_path = save_html_to_file(html, chart_date)
        
        logger.info(f"웹툰 차트 수집 완료: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"웹툰 차트 수집 중 오류 발생: {e}")
        return None


if __name__ == "__main__":
    # 테스트 실행
    setup_logging()
    result = extract_webtoon_chart()
    if result:
        print(f"수집 완료: {result}")
    else:
        print("수집 실패")

