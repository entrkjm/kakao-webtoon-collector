"""
카카오 웹툰 API 정렬 파라미터 테스트

다양한 정렬 파라미터를 시도하여 어떤 파라미터가 작동하는지 확인합니다.
"""

import json
import logging
import requests
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://gateway-kw.kakao.com/section/v2/timetables/days"

# 테스트할 파라미터 조합
TEST_PARAMS = [
    # 기본 placement만
    {'placement': 'timetable_mon'},
    
    # sort 파라미터 추가
    {'placement': 'timetable_mon', 'sort': 'popular'},
    {'placement': 'timetable_mon', 'sort': 'view'},
    {'placement': 'timetable_mon', 'sort': 'latest'},
    {'placement': 'timetable_mon', 'sort': 'male'},
    {'placement': 'timetable_mon', 'sort': 'female'},
    
    # order 파라미터 추가
    {'placement': 'timetable_mon', 'order': 'popular'},
    {'placement': 'timetable_mon', 'order': 'view'},
    {'placement': 'timetable_mon', 'order': 'latest'},
    {'placement': 'timetable_mon', 'order': 'male'},
    {'placement': 'timetable_mon', 'order': 'female'},
    
    # orderBy 파라미터
    {'placement': 'timetable_mon', 'orderBy': 'popular'},
    {'placement': 'timetable_mon', 'orderBy': 'view'},
    
    # 정렬 관련 다른 파라미터
    {'placement': 'timetable_mon', 'ranking': 'popular'},
    {'placement': 'timetable_mon', 'ranking': 'view'},
]


def test_api_with_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """파라미터로 API 호출 테스트"""
    
    url = BASE_URL
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Referer': 'https://webtoon.kakao.com/',
        'Origin': 'https://webtoon.kakao.com'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 웹툰 개수 확인
        webtoon_count = 0
        if isinstance(data, dict) and 'data' in data:
            for item in data.get('data', []):
                if isinstance(item, dict) and 'cardGroups' in item:
                    for card_group in item.get('cardGroups', []):
                        if isinstance(card_group, dict) and 'cards' in card_group:
                            webtoon_count += len(card_group.get('cards', []))
        
        # 첫 번째 웹툰 제목 확인 (순서 비교용)
        first_webtoon_title = None
        if isinstance(data, dict) and 'data' in data:
            for item in data.get('data', []):
                if isinstance(item, dict) and 'cardGroups' in item:
                    for card_group in item.get('cardGroups', []):
                        if isinstance(card_group, dict) and 'cards' in card_group:
                            cards = card_group.get('cards', [])
                            if cards and isinstance(cards[0], dict) and 'content' in cards[0]:
                                first_webtoon_title = cards[0]['content'].get('title')
                                break
                    if first_webtoon_title:
                        break
        
        return {
            'params': params,
            'status_code': response.status_code,
            'webtoon_count': webtoon_count,
            'first_webtoon_title': first_webtoon_title,
            'url': response.url,
            'success': True
        }
        
    except Exception as e:
        return {
            'params': params,
            'error': str(e),
            'success': False
        }


def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("카카오 웹툰 API 정렬 파라미터 테스트")
    logger.info("=" * 60)
    
    results = []
    
    for params in TEST_PARAMS:
        logger.info(f"\n테스트: {params}")
        result = test_api_with_params(params)
        results.append(result)
        
        if result.get('success'):
            logger.info(f"✓ 성공: {result['webtoon_count']}개 웹툰, 첫 번째: {result['first_webtoon_title']}")
        else:
            logger.error(f"✗ 실패: {result.get('error')}")
    
    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("결과 요약")
    logger.info("=" * 60)
    
    successful = [r for r in results if r.get('success')]
    logger.info(f"성공: {len(successful)}/{len(results)}")
    
    if len(successful) > 1:
        # 첫 번째 웹툰 제목 비교
        logger.info("\n첫 번째 웹툰 제목 비교:")
        for result in successful:
            logger.info(f"  {result['params']}: {result['first_webtoon_title']}")
        
        # 제목이 다른 경우 정렬이 다르다는 의미
        titles = [r['first_webtoon_title'] for r in successful]
        if len(set(titles)) > 1:
            logger.info("\n✓ 정렬이 다른 파라미터를 발견했습니다!")
            for result in successful:
                if result['first_webtoon_title'] != titles[0]:
                    logger.info(f"  다른 정렬: {result['params']}")
        else:
            logger.info("\n모든 파라미터가 같은 결과를 반환합니다.")
    
    # 결과 저장
    output_file = "data/analysis/sort_params_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"\n결과 저장: {output_file}")


if __name__ == "__main__":
    main()

