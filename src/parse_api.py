"""
API 응답 파싱 모듈

카카오 웹툰 API의 JSON 응답을 파싱합니다.
HTML 파싱과 별도로 관리합니다.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def sort_cards_by_sorting(cards: List[Dict[str, any]], sort_key: str) -> List[Dict[str, any]]:
    """
    카드 리스트를 sorting 정보를 사용하여 정렬합니다.
    
    Args:
        cards: 카드 리스트
        sort_key: 정렬 키 ('popularity', 'views', 'createdAt', 'popularityMale', 'popularityFemale')
    
    Returns:
        정렬된 카드 리스트
    """
    if not cards:
        return []
    
    def get_sort_value(card: dict) -> int:
        """카드에서 정렬 값 추출"""
        sorting = card.get('sorting', {})
        if isinstance(sorting, dict):
            return sorting.get(sort_key, 0)
        return 0
    
    # 내림차순 정렬 (높은 값이 먼저)
    sorted_cards = sorted(cards, key=get_sort_value, reverse=True)
    return sorted_cards


def parse_api_response(api_data: dict, sort_key: Optional[str] = None) -> List[Dict[str, any]]:
    """
    카카오 웹툰 API JSON 응답을 파싱하여 웹툰 차트 데이터 리스트로 변환합니다.
    
    API 응답 구조:
    {
        "_weekday": "mon",  # 최상위 레벨에 요일 정보
        "data": [
            {
                "cardGroups": [
                    {
                        "cards": [
                            {
                                "id": "웹툰 ID",
                                "content": {
                                    "title": "웹툰 제목",
                                    "authors": [{"name": "작가명", ...}, ...],
                                    ...
                                },
                                "sorting": {
                                    "popularity": 480,
                                    "views": 377,
                                    "createdAt": 95,
                                    "popularityMale": 710,
                                    "popularityFemale": 785
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    Args:
        api_data: API에서 받은 JSON 데이터
        sort_key: 정렬 키 (None이면 원본 순서 유지)
    
    Returns:
        웹툰 차트 데이터 리스트
        각 항목은 {'rank': int, 'title': str, 'webtoon_id': str, ...} 형식
    """
    chart_data = []
    
    try:
        # API 응답 구조: api_data['data'] -> cardGroups -> cards -> content
        if not isinstance(api_data, dict):
            logger.error(f"API 응답이 딕셔너리가 아닙니다: {type(api_data)}")
            return []
        
        # 최상위 레벨에서 요일 정보 추출 (단일 요일일 때 사용)
        default_weekday = api_data.get('_weekday')
        
        data_list = api_data.get('data', [])
        if not data_list:
            logger.warning("API 응답에서 'data' 필드를 찾을 수 없습니다.")
            return []
        
        logger.info(f"API 응답에서 {len(data_list)}개의 데이터 그룹 발견")
        
        rank = 1
        
        # data 배열 순회 (요일별 데이터 그룹)
        for data_item in data_list:
            if not isinstance(data_item, dict):
                continue
            
            # 요일 정보 추출: data_item에 _weekday가 있으면 사용, 없으면 최상위 레벨의 _weekday 사용
            weekday = data_item.get('_weekday') or default_weekday
            
            card_groups = data_item.get('cardGroups', [])
            if not card_groups:
                logger.warning("cardGroups를 찾을 수 없습니다.")
                continue
            
            # cardGroups 배열 순회
            for card_group in card_groups:
                if not isinstance(card_group, dict):
                    continue
                
                cards = card_group.get('cards', [])
                if not cards:
                    continue
                
                # 정렬 키가 지정된 경우 sorting 정보를 사용하여 정렬
                if sort_key:
                    cards = sort_cards_by_sorting(cards, sort_key)
                    logger.info(f"카드를 {sort_key} 기준으로 정렬: {len(cards)}개")
                
                # cards 배열 순회 (실제 웹툰 데이터)
                for card in cards:
                    if not isinstance(card, dict):
                        continue
                    
                    try:
                        webtoon_data = extract_webtoon_from_api_item(card, rank=rank, weekday=weekday)
                        if webtoon_data:
                            chart_data.append(webtoon_data)
                            rank += 1
                    except Exception as e:
                        logger.warning(f"항목 {rank} 파싱 실패: {e}")
                        continue
        
        logger.info(f"API 파싱 완료: {len(chart_data)}개 웹툰 데이터 추출")
        return chart_data
        
    except Exception as e:
        logger.error(f"API 응답 파싱 실패: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_webtoon_from_api_item(card: dict, rank: int, weekday: Optional[str] = None) -> Optional[Dict[str, any]]:
    """
    API 응답의 개별 카드(card) 항목에서 웹툰 데이터를 추출합니다.
    
    카드 구조:
    {
        "id": "웹툰 ID",
        "content": {
            "title": "웹툰 제목",
            "authors": [{"name": "작가명", "type": "AUTHOR", ...}, ...],
            ...
        }
    }
    
    Args:
        card: API 응답의 개별 카드 항목 (딕셔너리)
        rank: 순위
        weekday: 요일 정보 ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
    
    Returns:
        웹툰 데이터 딕셔너리 (실패 시 None)
    """
    try:
        # 카드의 id가 웹툰 ID
        webtoon_id = card.get('id')
        if not webtoon_id:
            logger.warning(f"순위 {rank}: 웹툰 ID를 찾을 수 없습니다 (card.id)")
            return None
        webtoon_id = str(webtoon_id)
        
        # content 객체에서 웹툰 정보 추출
        content = card.get('content', {})
        if not isinstance(content, dict):
            logger.warning(f"순위 {rank}: content를 찾을 수 없습니다")
            return None
        
        # 제목 추출
        title = content.get('title')
        if not title:
            logger.warning(f"순위 {rank}: 제목을 찾을 수 없습니다 (content.title)")
            return None
        title = str(title)
        
        # 작가 추출 (선택적)
        # authors는 배열: [{"name": "작가명", "type": "AUTHOR", ...}, ...]
        author = None
        authors_list = content.get('authors', [])
        if authors_list and isinstance(authors_list, list):
            # AUTHOR 타입만 추출
            author_names = [
                a.get('name') for a in authors_list 
                if isinstance(a, dict) and a.get('type') == 'AUTHOR'
            ]
            if author_names:
                # 여러 작가가 있으면 쉼표로 구분
                author = ', '.join(str(name) for name in author_names if name)
        
        # 장르 추출 (card.genreFilters에서 "all" 제외한 첫 번째 값)
        genre = None
        genre_filters = card.get('genreFilters', [])
        if genre_filters and isinstance(genre_filters, list):
            # "all"을 제외한 첫 번째 값 사용
            genre_list = [g for g in genre_filters if g != 'all']
            if genre_list:
                genre = genre_list[0]
        
        # 태그 추출 (content.seoKeywords에서 "#" 제거)
        tags = None
        seo_keywords = content.get('seoKeywords', [])
        if seo_keywords and isinstance(seo_keywords, list):
            tags = [str(kw).lstrip('#') for kw in seo_keywords if kw]
        
        # SEO ID 추출
        seo_id = content.get('seoId')
        
        # 성인 여부 추출
        adult = content.get('adult')
        
        # 캐치프레이즈 추출
        catchphrase = content.get('catchphraseTwoLines')
        
        # 배지 추출 (content.badges의 title만)
        badges = None
        badges_list = content.get('badges', [])
        if badges_list and isinstance(badges_list, list):
            badges = [b.get('title') for b in badges_list if isinstance(b, dict) and b.get('title')]
        
        # 콘텐츠 ID 추출 (content.id)
        content_id = content.get('id')
        
        # 조회수 추출 (선택적, 있으면)
        # API 응답 구조 확인 필요: content에 직접 있거나, card 레벨에 있을 수 있음
        view_count = content.get('viewCount') or content.get('view_count') or card.get('viewCount') or card.get('view_count')
        if view_count is not None:
            try:
                view_count = int(view_count)
            except (ValueError, TypeError):
                view_count = None
        
        # sorting 정보에서 views 값 사용 (view_count가 없을 경우)
        if view_count is None:
            sorting = card.get('sorting', {})
            if isinstance(sorting, dict) and 'views' in sorting:
                try:
                    view_count = int(sorting['views'])
                except (ValueError, TypeError):
                    view_count = None
        
        # 기본 데이터 구성
        data = {
            'rank': rank,
            'title': title,
            'webtoon_id': webtoon_id,
        }
        
        # 선택적 필드 추가
        if author:
            data['author'] = author
        
        if genre:
            data['genre'] = genre
        
        if tags:
            data['tags'] = tags
        
        if seo_id:
            data['seo_id'] = seo_id
        
        if adult is not None:
            data['adult'] = adult
        
        if catchphrase:
            data['catchphrase'] = catchphrase
        
        if badges:
            data['badges'] = badges
        
        if content_id is not None:
            data['content_id'] = content_id
        
        if view_count is not None:
            data['view_count'] = view_count
        
        if weekday:
            data['weekday'] = weekday
        
        return data
        
    except Exception as e:
        logger.error(f"데이터 추출 실패 (순위 {rank}): {e}")
        import traceback
        traceback.print_exc()
        return None

