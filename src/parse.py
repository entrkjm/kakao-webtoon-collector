"""
Parse 모듈: HTML에서 차트 데이터 파싱

이 모듈은 수집된 HTML에서 웹툰 차트 데이터를 추출합니다.
- 순위
- 제목
- 웹툰 ID
등을 파싱합니다.

주의: 실제 HTML 구조에 따라 CSS 선택자가 수정될 수 있습니다.
여러 선택자를 시도하여 유연하게 대응합니다.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def load_html_from_file(file_path: Path) -> Optional[str]:
    """
    HTML 파일을 읽어옵니다.
    
    Args:
        file_path: HTML 파일 경로
    
    Returns:
        HTML 문자열 (실패 시 None)
    """
    try:
        html = file_path.read_text(encoding='utf-8')
        logger.info(f"HTML 파일 로드 성공: {file_path}")
        return html
    except Exception as e:
        logger.error(f"HTML 파일 로드 실패: {file_path}, 오류: {e}")
        return None


def parse_webtoon_chart_html(html: str) -> List[Dict[str, any]]:
    """
    HTML에서 웹툰 차트 데이터를 파싱합니다.
    
    실제 HTML 구조에 따라 CSS 선택자가 수정될 수 있습니다.
    여러 선택자를 시도하여 유연하게 대응합니다.
    
    Args:
        html: 파싱할 HTML 문자열
    
    Returns:
        웹툰 차트 데이터 리스트
        각 항목은 {'rank': int, 'title': str, 'webtoon_id': str, ...} 형식
    """
    soup = BeautifulSoup(html, 'lxml')
    chart_data = []
    
    # 카카오 웹툰 HTML 구조에 맞는 선택자 (실제 구조 확인 후 수정 필요)
    selectors = [
        'a[href*="/viewer/"]',  # 카카오 웹툰 링크 패턴 (예상)
        'div.item a[href*="webtoon"]',
        'li.item a[href*="webtoon"]',
        'div.area_toon a',
    ]
    
    items = None
    used_selector = None
    
    for selector in selectors:
        items = soup.select(selector)
        if items and len(items) > 10:
            used_selector = selector
            logger.info(f"파싱 성공: 선택자 '{selector}' 사용, {len(items)}개 항목 발견")
            break
    
    if not items:
        logger.warning("웹툰 차트 항목을 찾을 수 없습니다. HTML 구조를 확인하세요.")
        return []
    
    for idx, item in enumerate(items, start=1):
        try:
            webtoon_data = extract_webtoon_data(item, rank=idx)
            if webtoon_data:
                chart_data.append(webtoon_data)
        except Exception as e:
            logger.warning(f"항목 {idx} 파싱 실패: {e}")
            continue
    
    logger.info(f"파싱 완료: {len(chart_data)}개 웹툰 데이터 추출")
    return chart_data


def extract_webtoon_data(item, rank: int) -> Optional[Dict[str, any]]:
    """
    개별 웹툰 항목에서 데이터를 추출합니다.
    
    실제 HTML 구조에 따라 이 함수를 수정해야 합니다.
    
    Args:
        item: BeautifulSoup 요소
        rank: 순위
    
    Returns:
        웹툰 데이터 딕셔너리 (실패 시 None)
    """
    try:
        # 카카오 웹툰 구조에 맞게 수정 필요
        link_elem = item if item.name == 'a' else item.select_one('a')
        if not link_elem:
            logger.warning(f"순위 {rank}: 링크를 찾을 수 없습니다")
            return None
        
        href = link_elem.get('href', '')
        
        # 웹툰 ID 추출 (카카오 웹툰 URL 패턴 확인 필요)
        # 예: /viewer/123456 또는 /webtoon/viewer/123456
        webtoon_id = None
        if '/viewer/' in href:
            parts = href.split('/viewer/')
            if len(parts) > 1:
                webtoon_id = parts[1].split('/')[0].split('?')[0]
        
        if not webtoon_id:
            logger.warning(f"순위 {rank}: 웹툰 ID를 찾을 수 없습니다 (href: {href})")
            return None
        
        # 제목 추출
        title = None
        title_selectors = [
            '.title',
            'span.title',
            'div.title',
            'h3',
            'h4',
        ]
        
        for selector in title_selectors:
            title_elem = item.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 2:
                    break
        
        if not title:
            title = link_elem.get_text(strip=True)
            if '\n' in title:
                title = title.split('\n')[0].strip()
        
        if not title or len(title) < 2:
            logger.warning(f"순위 {rank}: 제목을 찾을 수 없습니다")
            return None
        
        # 작가 정보 추출
        author = None
        author_elem = item.select_one('.author, .writer, span.author')
        if author_elem:
            author = author_elem.get_text(strip=True)
        
        data = {
            'rank': rank,
            'title': title,
            'webtoon_id': webtoon_id,
        }
        
        if author:
            data['author'] = author
        
        return data
        
    except Exception as e:
        logger.error(f"데이터 추출 실패 (순위 {rank}): {e}")
        return None


def parse_html_file(file_path: Path) -> List[Dict[str, any]]:
    """
    HTML 파일을 읽어서 파싱합니다.
    API 응답이 포함된 경우 API 파서를 사용합니다.
    
    Args:
        file_path: HTML 파일 경로
    
    Returns:
        웹툰 차트 데이터 리스트
    """
    html = load_html_from_file(file_path)
    if html is None:
        return []
    
    # API 응답이 포함된 경우
    if 'application/json' in html and 'webtoon-data' in html:
        try:
            import json
            import re
            from src.parse_api import parse_api_response
            
            json_match = re.search(r'<script[^>]*id=[\'"]webtoon-data[\'"][^>]*>(.*?)</script>', html, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                api_data = json.loads(json_str)
                logger.info("API 응답 데이터 발견, API 파서 사용")
                
                # 정렬 키 추출 (메타데이터에서)
                sort_key = api_data.get('_sort_key')
                
                return parse_api_response(api_data, sort_key=sort_key)
        except Exception as e:
            logger.warning(f"API 응답 파싱 실패, HTML 파서로 전환: {e}")
    
    return parse_webtoon_chart_html(html)


if __name__ == "__main__":
    # 테스트 실행
    import sys
    from src.utils import setup_logging
    
    setup_logging()
    
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
        data = parse_html_file(file_path)
        print(f"파싱 결과: {len(data)}개 항목")
        for item in data[:5]:
            print(item)
    else:
        print("사용법: python parse.py <html_file_path>")

