"""
데이터 모델 정의

이 모듈은 데이터 모델 스키마를 정의합니다.
- dim_webtoon: 웹툰 마스터 테이블 스키마
- fact_weekly_chart: 주간 차트 히스토리 테이블 스키마
"""

from datetime import date, datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# dim_webtoon (마스터 테이블) 스키마
# ============================================================================

def create_dim_webtoon_record(
    webtoon_id: str,
    title: str,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    tags: Optional[list] = None,
    seo_id: Optional[str] = None,
    adult: Optional[bool] = None,
    catchphrase: Optional[str] = None,
    badges: Optional[list] = None,
    content_id: Optional[int] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    dim_webtoon 레코드를 생성합니다.
    
    Args:
        webtoon_id: 웹툰 고유 ID (필수, Primary Key)
        title: 웹툰 제목 (필수)
        author: 작가명 (선택)
        genre: 장르 (선택, card.genreFilters에서 추출)
        tags: 태그 리스트 (선택, content.seoKeywords에서 추출)
        seo_id: SEO ID (선택, content.seoId)
        adult: 성인 여부 (선택, content.adult)
        catchphrase: 캐치프레이즈 (선택, content.catchphraseTwoLines)
        badges: 배지 리스트 (선택, content.badges의 title)
        content_id: 콘텐츠 숫자 ID (선택, content.id)
        created_at: 레코드 생성 시각 (선택, 없으면 현재 시각)
        updated_at: 레코드 수정 시각 (선택, 없으면 현재 시각)
    
    Returns:
        dim_webtoon 레코드 딕셔너리
    
    Raises:
        ValueError: 필수 필드가 누락된 경우
    """
    if not webtoon_id:
        raise ValueError("webtoon_id는 필수 필드입니다.")
    if not title:
        raise ValueError("title은 필수 필드입니다.")
    
    now = datetime.now()
    
    # tags는 리스트로 저장 (BigQuery에서는 REPEATED STRING으로 사용)
    tags_list = None
    if tags:
        if isinstance(tags, list):
            tags_list = [str(tag) for tag in tags if tag]
        elif isinstance(tags, str):
            tags_list = [t.strip() for t in tags.split('|') if t.strip()]
        else:
            tags_list = [str(tags)]
    
    # badges는 리스트로 저장 (BigQuery에서는 REPEATED STRING으로 사용)
    badges_list = None
    if badges:
        if isinstance(badges, list):
            badges_list = [str(badge) for badge in badges if badge]
        elif isinstance(badges, str):
            badges_list = [b.strip() for b in badges.split('|') if b.strip()]
        else:
            badges_list = [str(badges)]
    
    return {
        'webtoon_id': str(webtoon_id),
        'title': str(title),
        'author': str(author) if author else None,
        'genre': str(genre) if genre else None,
        'tags': tags_list,
        'seo_id': str(seo_id) if seo_id else None,
        'adult': bool(adult) if adult is not None else None,
        'catchphrase': str(catchphrase) if catchphrase else None,
        'badges': badges_list,
        'content_id': int(content_id) if content_id is not None else None,
        'created_at': created_at if created_at else now,
        'updated_at': updated_at if updated_at else now
    }


def validate_dim_webtoon_record(record: Dict[str, Any]) -> bool:
    """
    dim_webtoon 레코드의 유효성을 검증합니다.
    
    Args:
        record: 검증할 레코드
    
    Returns:
        유효하면 True, 그렇지 않으면 False
    """
    required_fields = ['webtoon_id', 'title']
    
    for field in required_fields:
        if field not in record or not record[field]:
            logger.warning(f"dim_webtoon 레코드 검증 실패: 필수 필드 '{field}' 누락")
            return False
    
    if not isinstance(record['webtoon_id'], str):
        logger.warning(f"dim_webtoon 레코드 검증 실패: webtoon_id는 문자열이어야 합니다")
        return False
    
    return True


# ============================================================================
# fact_weekly_chart (히스토리 테이블) 스키마
# ============================================================================

def create_fact_weekly_chart_record(
    chart_date: date,
    webtoon_id: str,
    rank: int,
    collected_at: Optional[datetime] = None,
    weekday: Optional[str] = None,
    weekday_rank: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    week: Optional[int] = None,
    view_count: Optional[int] = None,
    sort_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    fact_weekly_chart 레코드를 생성합니다.
    
    Args:
        chart_date: 수집 날짜 (필수, Partition Key)
        webtoon_id: 웹툰 ID (필수, Foreign Key -> dim_webtoon)
        rank: 주간 차트 순위 (필수, 1 이상의 정수) - 통합 순위 (모든 요일 통합)
        collected_at: 데이터 수집 시각 (선택, 없으면 현재 시각)
        weekday: 요일 정보 (선택)
        weekday_rank: 요일별 순위 (선택, 각 요일 내에서 1, 2, 3, ... 순위)
        year: 연도 (선택, collected_at에서 추출)
        month: 월 (선택, collected_at에서 추출)
        week: 해당 월의 몇 번째 주인지 (선택, collected_at에서 추출)
        view_count: 조회수 (선택)
    
    Returns:
        fact_weekly_chart 레코드 딕셔너리
    
    Raises:
        ValueError: 필수 필드가 누락되었거나 유효하지 않은 경우
    """
    if not chart_date:
        raise ValueError("chart_date는 필수 필드입니다.")
    if not webtoon_id:
        raise ValueError("webtoon_id는 필수 필드입니다.")
    if not isinstance(rank, int) or rank < 1:
        raise ValueError("rank는 1 이상의 정수여야 합니다.")
    
    now = datetime.now() if not collected_at else collected_at
    
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    if week is None:
        day_of_month = now.day
        week = ((day_of_month - 1) // 7) + 1
    
    return {
        'chart_date': chart_date if isinstance(chart_date, date) else chart_date,
        'webtoon_id': str(webtoon_id),
        'rank': int(rank),  # 통합 순위 (모든 요일 통합)
        'collected_at': now,
        'weekday': weekday,  # 요일 정보
        'weekday_rank': int(weekday_rank) if weekday_rank is not None else None,  # 요일별 순위
        'year': int(year),
        'month': int(month),
        'week': int(week),
        'view_count': int(view_count) if view_count is not None else None,
        'sort_key': sort_key
    }


def validate_fact_weekly_chart_record(record: Dict[str, Any]) -> bool:
    """
    fact_weekly_chart 레코드의 유효성을 검증합니다.
    
    Args:
        record: 검증할 레코드
    
    Returns:
        유효하면 True, 그렇지 않으면 False
    """
    required_fields = ['chart_date', 'webtoon_id', 'rank']
    
    for field in required_fields:
        if field not in record:
            logger.warning(f"fact_weekly_chart 레코드 검증 실패: 필수 필드 '{field}' 누락")
            return False
    
    if not isinstance(record['chart_date'], (date, str)):
        logger.warning(f"fact_weekly_chart 레코드 검증 실패: chart_date는 date 타입이어야 합니다")
        return False
    
    if not isinstance(record['webtoon_id'], str) or not record['webtoon_id']:
        logger.warning(f"fact_weekly_chart 레코드 검증 실패: webtoon_id는 비어있지 않은 문자열이어야 합니다")
        return False
    
    if not isinstance(record['rank'], int) or record['rank'] < 1:
        logger.warning(f"fact_weekly_chart 레코드 검증 실패: rank는 1 이상의 정수여야 합니다 (현재: {record['rank']})")
        return False
    
    return True


# ============================================================================
# 스키마 정의 (참조용)
# ============================================================================

DIM_WEBTOON_SCHEMA = {
    'webtoon_id': str,
    'title': str,
    'author': Optional[str],
    'genre': Optional[str],
    'tags': Optional[list],
    'created_at': datetime,
    'updated_at': datetime
}

FACT_WEEKLY_CHART_SCHEMA = {
    'chart_date': date,
    'webtoon_id': str,
    'rank': int,
    'collected_at': datetime,
    'weekday': Optional[str],
    'weekday_rank': Optional[int],  # 요일별 순위 (각 요일 내에서 1, 2, 3, ...)
    'year': int,
    'month': int,
    'week': int,
    'view_count': Optional[int]
}

DIM_WEBTOON_COLUMNS = [
    'webtoon_id',
    'title',
    'author',
    'genre',
    'tags',
    'seo_id',
    'adult',
    'catchphrase',
    'badges',
    'content_id',
    'created_at',
    'updated_at'
]

FACT_WEEKLY_CHART_COLUMNS = [
    'chart_date',
    'webtoon_id',
    'rank',
    'collected_at',
    'weekday',
    'weekday_rank',
    'year',
    'month',
    'week',
    'view_count',
    'sort_key'
]


# ============================================================================
# Foreign Key 관계 검증
# ============================================================================

def validate_foreign_key(
    fact_record: Dict[str, Any],
    dim_webtoon_ids: set
) -> bool:
    """
    fact_weekly_chart 레코드의 webtoon_id가 dim_webtoon에 존재하는지 검증합니다.
    
    Args:
        fact_record: fact_weekly_chart 레코드
        dim_webtoon_ids: dim_webtoon에 존재하는 webtoon_id 집합
    
    Returns:
        Foreign Key 관계가 유효하면 True, 그렇지 않으면 False
    """
    webtoon_id = fact_record.get('webtoon_id')
    
    if not webtoon_id:
        logger.warning("Foreign Key 검증 실패: webtoon_id가 없습니다")
        return False
    
    if webtoon_id not in dim_webtoon_ids:
        logger.warning(f"Foreign Key 검증 실패: webtoon_id '{webtoon_id}'가 dim_webtoon에 존재하지 않습니다")
        return False
    
    return True

