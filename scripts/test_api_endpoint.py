"""
발견한 API 엔드포인트 테스트

발견한 API:
- https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon
- https://gateway-kw.kakao.com/section/v2/timetables/days?placement=timetable_mon_free_publishing
"""

import json
import logging
import requests
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://gateway-kw.kakao.com/section/v2/timetables/days"

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
    '기다무': '_wait_free'  # 추정
}


def test_api_endpoint(weekday: str = 'mon', filter_type: str = '') -> Dict[Any, Any]:
    """API 엔드포인트 테스트"""
    
    # placement 파라미터 구성
    placement = f"timetable_{weekday}"
    if filter_type:
        placement += filter_type
    
    url = f"{BASE_URL}?placement={placement}"
    
    logger.info(f"API 호출: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Referer': 'https://webtoon.kakao.com/',
        'Origin': 'https://webtoon.kakao.com'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        logger.info(f"✓ 성공: {response.status_code}")
        
        data = response.json()
        logger.info(f"응답 타입: {type(data)}")
        
        if isinstance(data, dict):
            logger.info(f"응답 키: {list(data.keys())[:10]}")
        
        return {
            'url': url,
            'status_code': response.status_code,
            'data': data,
            'headers': dict(response.headers)
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ 실패: {e}")
        return {
            'url': url,
            'error': str(e)
        }


def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("발견한 API 엔드포인트 테스트")
    logger.info("=" * 60)
    
    # 테스트 케이스
    test_cases = [
        ('mon', ''),  # 월요일 전체
        ('mon', '_free_publishing'),  # 월요일 연재무료
        ('wed', ''),  # 수요일 전체
        ('wed', '_free_publishing'),  # 수요일 연재무료
    ]
    
    results = []
    
    for weekday, filter_type in test_cases:
        logger.info(f"\n테스트: {weekday} + {filter_type}")
        result = test_api_endpoint(weekday, filter_type)
        results.append(result)
        
        if 'data' in result:
            # 데이터 구조 확인
            data = result['data']
            logger.info(f"데이터 구조: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    
    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("결과 요약")
    logger.info("=" * 60)
    
    success_count = sum(1 for r in results if 'data' in r)
    logger.info(f"성공: {success_count}/{len(results)}")
    
    if success_count > 0:
        logger.info("\n✓ API 엔드포인트가 작동합니다!")
        logger.info("이제 이 API를 사용하여 데이터를 수집할 수 있습니다.")
    else:
        logger.warning("\n✗ API 엔드포인트 테스트 실패")
        logger.warning("인증이나 다른 요구사항이 필요할 수 있습니다.")


if __name__ == "__main__":
    main()

