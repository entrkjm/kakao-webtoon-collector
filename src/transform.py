"""
Transform 모듈: 데이터 변환 및 정규화

이 모듈은 파싱된 데이터를 스키마에 맞게 변환하고 CSV로 저장합니다.
- dim_webtoon (마스터 테이블) 데이터 생성 및 저장
- fact_weekly_chart (히스토리 테이블) 데이터 생성 및 저장
- 멱등성 보장 (중복 체크)

주의: 실제 수집되는 데이터 필드에 따라 스키마가 수정될 수 있습니다.
"""

import csv
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd

from src.models import (
    create_dim_webtoon_record,
    create_fact_weekly_chart_record,
    validate_dim_webtoon_record,
    validate_fact_weekly_chart_record,
    validate_foreign_key,
    DIM_WEBTOON_COLUMNS,
    FACT_WEEKLY_CHART_COLUMNS,
)
from src.utils import (
    get_chart_csv_path,
    get_chart_jsonl_path,
    get_dim_webtoon_csv_path,
    get_dim_webtoon_jsonl_path,
    get_data_format,
    format_date,
    format_datetime,
    parse_date,
    parse_datetime,
    setup_logging,
    ensure_dir,
)

logger = logging.getLogger(__name__)


def serialize_for_json(obj):
    """
    JSON 직렬화를 위한 헬퍼 함수.
    datetime, date 객체를 문자열로 변환합니다.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def load_dim_webtoon_jsonl() -> pd.DataFrame:
    """
    dim_webtoon JSONL 파일을 로드합니다. 파일이 없으면 빈 DataFrame 반환.
    
    Returns:
        dim_webtoon DataFrame
    """
    file_path = get_dim_webtoon_jsonl_path()
    
    if not file_path.exists():
        logger.info("dim_webtoon.jsonl 파일이 없습니다. 새로 생성합니다.")
        return pd.DataFrame(columns=DIM_WEBTOON_COLUMNS)
    
    try:
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    # datetime 문자열을 datetime 객체로 변환
                    if 'created_at' in record and record['created_at']:
                        record['created_at'] = datetime.fromisoformat(record['created_at'].replace('Z', '+00:00'))
                    if 'updated_at' in record and record['updated_at']:
                        record['updated_at'] = datetime.fromisoformat(record['updated_at'].replace('Z', '+00:00'))
                    records.append(record)
        
        if len(records) == 0:
            return pd.DataFrame(columns=DIM_WEBTOON_COLUMNS)
        
        df = pd.DataFrame(records)
        logger.info(f"dim_webtoon.jsonl 로드 완료: {len(df)}개 레코드")
        return df
    except Exception as e:
        logger.error(f"dim_webtoon.jsonl 로드 실패: {e}")
        return pd.DataFrame(columns=DIM_WEBTOON_COLUMNS)


def load_dim_webtoon() -> pd.DataFrame:
    """
    dim_webtoon 파일을 로드합니다 (JSONL 또는 CSV).
    DATA_FORMAT 환경 변수에 따라 형식을 결정합니다.
    
    Returns:
        dim_webtoon DataFrame
    """
    data_format = get_data_format()
    if data_format == 'jsonl':
        return load_dim_webtoon_jsonl()
    else:
        return load_dim_webtoon_csv()


def load_dim_webtoon_csv() -> pd.DataFrame:
    """
    dim_webtoon CSV 파일을 로드합니다. 파일이 없으면 빈 DataFrame 반환.
    
    Returns:
        dim_webtoon DataFrame
    """
    file_path = get_dim_webtoon_csv_path()
    
    if not file_path.exists():
        logger.info("dim_webtoon.csv 파일이 없습니다. 새로 생성합니다.")
        return pd.DataFrame(columns=DIM_WEBTOON_COLUMNS)
    
    try:
        df = pd.read_csv(file_path)
        
        # 기존 CSV와의 호환성: tags 컬럼이 없으면 추가
        if 'tags' not in df.columns:
            df['tags'] = None
            logger.debug("기존 CSV에 tags 컬럼이 없어 추가했습니다.")
        
        # tags를 파이프로 구분된 문자열에서 리스트로 변환 (BigQuery REPEATED STRING용)
        if 'tags' in df.columns:
            def convert_tags_to_list(tags_str):
                if tags_str is None or (isinstance(tags_str, float) and pd.isna(tags_str)):
                    return None
                if isinstance(tags_str, list):
                    return tags_str  # 이미 리스트인 경우
                if isinstance(tags_str, str):
                    return [t.strip() for t in tags_str.split('|') if t.strip()]
                return None
            
            df['tags'] = df['tags'].apply(convert_tags_to_list)
        
        # created_at, updated_at을 datetime 타입으로 변환
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        if 'updated_at' in df.columns:
            df['updated_at'] = pd.to_datetime(df['updated_at'])
        
        logger.info(f"dim_webtoon.csv 로드 완료: {len(df)}개 레코드")
        return df
    except Exception as e:
        logger.error(f"dim_webtoon.csv 로드 실패: {e}")
        return pd.DataFrame(columns=DIM_WEBTOON_COLUMNS)


def load_fact_weekly_chart_jsonl(chart_date: date) -> pd.DataFrame:
    """
    fact_weekly_chart JSONL 파일을 로드합니다 (날짜별 파일).
    파일이 없으면 빈 DataFrame 반환.
    
    Args:
        chart_date: 수집 날짜
    
    Returns:
        fact_weekly_chart DataFrame
    """
    file_path = get_chart_jsonl_path(chart_date)
    
    if not file_path.exists():
        logger.info(f"fact_weekly_chart {format_date(chart_date)}.jsonl 파일이 없습니다.")
        return pd.DataFrame(columns=FACT_WEEKLY_CHART_COLUMNS)
    
    try:
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    # date, datetime 문자열을 객체로 변환
                    if 'chart_date' in record and record['chart_date']:
                        record['chart_date'] = date.fromisoformat(record['chart_date'])
                    if 'collected_at' in record and record['collected_at']:
                        record['collected_at'] = datetime.fromisoformat(record['collected_at'].replace('Z', '+00:00'))
                    records.append(record)
        
        if len(records) == 0:
            return pd.DataFrame(columns=FACT_WEEKLY_CHART_COLUMNS)
        
        df = pd.DataFrame(records)
        logger.info(f"fact_weekly_chart {format_date(chart_date)}.jsonl 로드 완료: {len(df)}개 레코드")
        return df
    except Exception as e:
        logger.error(f"fact_weekly_chart JSONL 로드 실패: {e}")
        return pd.DataFrame(columns=FACT_WEEKLY_CHART_COLUMNS)


def load_fact_weekly_chart(chart_date: date) -> pd.DataFrame:
    """
    fact_weekly_chart 파일을 로드합니다 (JSONL 또는 CSV).
    DATA_FORMAT 환경 변수에 따라 형식을 결정합니다.
    
    Args:
        chart_date: 수집 날짜
    
    Returns:
        fact_weekly_chart DataFrame
    """
    data_format = get_data_format()
    if data_format == 'jsonl':
        return load_fact_weekly_chart_jsonl(chart_date)
    else:
        return load_fact_weekly_chart_csv(chart_date)


def load_fact_weekly_chart_csv(chart_date: date) -> pd.DataFrame:
    """
    fact_weekly_chart CSV 파일을 로드합니다 (날짜별 파일).
    파일이 없으면 빈 DataFrame 반환.
    
    Args:
        chart_date: 수집 날짜
    
    Returns:
        fact_weekly_chart DataFrame
    """
    file_path = get_chart_csv_path(chart_date)
    
    if not file_path.exists():
        logger.info(f"fact_weekly_chart {format_date(chart_date)}.csv 파일이 없습니다.")
        return pd.DataFrame(columns=FACT_WEEKLY_CHART_COLUMNS)
    
    try:
        df = pd.read_csv(file_path)
        # chart_date를 date 타입으로 변환
        if 'chart_date' in df.columns:
            df['chart_date'] = pd.to_datetime(df['chart_date']).dt.date
        
        # 기존 CSV 파일과의 호환성: 새로운 컬럼이 없으면 기본값 설정
        for col in FACT_WEEKLY_CHART_COLUMNS:
            if col not in df.columns:
                if col == 'weekday':
                    df[col] = None
                elif col in ['year', 'month', 'week']:
                    # collected_at에서 추출
                    if 'collected_at' in df.columns:
                        df['collected_at'] = pd.to_datetime(df['collected_at'])
                        if col == 'year':
                            df[col] = df['collected_at'].dt.year
                        elif col == 'month':
                            df[col] = df['collected_at'].dt.month
                        elif col == 'week':
                            # 해당 월의 몇 번째 주인지 계산
                            df[col] = ((df['collected_at'].dt.day - 1) // 7) + 1
                    else:
                        # collected_at도 없으면 현재 시각에서 추출
                        now = datetime.now()
                        if col == 'year':
                            df[col] = now.year
                        elif col == 'month':
                            df[col] = now.month
                        elif col == 'week':
                            df[col] = ((now.day - 1) // 7) + 1
                elif col == 'view_count':
                    df[col] = None
        
        logger.info(f"fact_weekly_chart {format_date(chart_date)}.csv 로드 완료: {len(df)}개 레코드")
        return df
    except Exception as e:
        logger.error(f"fact_weekly_chart CSV 로드 실패: {e}")
        return pd.DataFrame(columns=FACT_WEEKLY_CHART_COLUMNS)


def save_dim_webtoon_jsonl(df: pd.DataFrame) -> None:
    """
    dim_webtoon DataFrame을 JSONL 파일로 저장합니다.
    
    tags는 리스트 그대로 저장됩니다 (BigQuery REPEATED STRING용).
    
    Args:
        df: 저장할 DataFrame
    """
    file_path = get_dim_webtoon_jsonl_path()
    
    try:
        # 컬럼 순서 보장
        df = df[DIM_WEBTOON_COLUMNS].copy() if all(col in df.columns for col in DIM_WEBTOON_COLUMNS) else df.copy()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for _, row in df.iterrows():
                record = row.to_dict()
                # datetime을 ISO 형식 문자열로 변환
                if 'created_at' in record and pd.notna(record['created_at']):
                    if isinstance(record['created_at'], pd.Timestamp):
                        record['created_at'] = record['created_at'].isoformat()
                if 'updated_at' in record and pd.notna(record['updated_at']):
                    if isinstance(record['updated_at'], pd.Timestamp):
                        record['updated_at'] = record['updated_at'].isoformat()
                # None을 null로 변환 (리스트는 그대로 유지)
                def convert_value(val):
                    if isinstance(val, list):
                        return val  # 리스트는 그대로
                    if pd.isna(val):
                        return None
                    return val
                record = {k: convert_value(v) for k, v in record.items()}
                f.write(json.dumps(record, ensure_ascii=False, default=serialize_for_json) + '\n')
        
        logger.info(f"dim_webtoon.jsonl 저장 완료: {len(df)}개 레코드")
    except Exception as e:
        logger.error(f"dim_webtoon.jsonl 저장 실패: {e}")
        raise


def save_dim_webtoon_csv(df: pd.DataFrame) -> None:
    """
    dim_webtoon DataFrame을 CSV 파일로 저장합니다.
    
    tags는 리스트인 경우 파이프로 구분된 문자열로 변환하여 저장합니다.
    (BigQuery 적재 시에는 리스트를 REPEATED STRING으로 변환)
    
    Args:
        df: 저장할 DataFrame
    """
    file_path = get_dim_webtoon_csv_path()
    
    try:
        # 컬럼 순서 보장
        df = df[DIM_WEBTOON_COLUMNS].copy() if all(col in df.columns for col in DIM_WEBTOON_COLUMNS) else df.copy()
        
        # tags를 리스트에서 파이프로 구분된 문자열로 변환 (CSV 저장용)
        if 'tags' in df.columns:
            def convert_tags_to_string(tags):
                if tags is None or (isinstance(tags, float) and pd.isna(tags)):
                    return None
                if isinstance(tags, list):
                    return '|'.join(str(tag) for tag in tags if tag)
                return str(tags) if tags else None
            
            df['tags'] = df['tags'].apply(convert_tags_to_string)
        
        df.to_csv(file_path, index=False, encoding='utf-8')
        logger.info(f"dim_webtoon.csv 저장 완료: {len(df)}개 레코드")
    except Exception as e:
        logger.error(f"dim_webtoon.csv 저장 실패: {e}")
        raise


def save_dim_webtoon(df: pd.DataFrame) -> None:
    """
    dim_webtoon DataFrame을 저장합니다 (JSONL 또는 CSV).
    DATA_FORMAT 환경 변수에 따라 형식을 결정합니다.
    
    Args:
        df: 저장할 DataFrame
    """
    data_format = get_data_format()
    if data_format == 'jsonl':
        save_dim_webtoon_jsonl(df)
    else:
        save_dim_webtoon_csv(df)


def save_fact_weekly_chart_jsonl(df: pd.DataFrame, chart_date: date, sort_key: Optional[str] = None) -> None:
    """
    fact_weekly_chart DataFrame을 JSONL 파일로 저장합니다 (날짜별 파일).
    
    Args:
        df: 저장할 DataFrame
        chart_date: 수집 날짜
        sort_key: 정렬 키 (None이면 기본 파일명)
    """
    file_path = get_chart_jsonl_path(chart_date, sort_key)
    ensure_dir(file_path.parent)
    
    # datetime 객체를 문자열로 변환하는 헬퍼 함수
    def serialize_for_json(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    records = df.to_dict(orient='records')
    with open(file_path, 'w', encoding='utf-8') as f:
        for record in records:
            # NaN 값을 None으로 변환 (JSON null)
            record = {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in record.items()}
            f.write(json.dumps(record, ensure_ascii=False, default=serialize_for_json) + '\n')
    
    logger.info(f"fact_weekly_chart {format_date(chart_date)}.jsonl 저장 완료: {len(df)}개 레코드")


def save_fact_weekly_chart_csv(df: pd.DataFrame, chart_date: date) -> None:
    """
    fact_weekly_chart DataFrame을 CSV 파일로 저장합니다 (날짜별 파일).
    
    Args:
        df: 저장할 DataFrame
        chart_date: 수집 날짜
    """
    file_path = get_chart_csv_path(chart_date)
    
    try:
        # 컬럼 순서 보장
        df = df[FACT_WEEKLY_CHART_COLUMNS] if all(col in df.columns for col in FACT_WEEKLY_CHART_COLUMNS) else df
        df.to_csv(file_path, index=False, encoding='utf-8')
        logger.info(f"fact_weekly_chart {format_date(chart_date)}.csv 저장 완료: {len(df)}개 레코드")
    except Exception as e:
        logger.error(f"fact_weekly_chart CSV 저장 실패: {e}")
        raise


def save_fact_weekly_chart(df: pd.DataFrame, chart_date: date, sort_key: Optional[str] = None) -> None:
    """
    fact_weekly_chart DataFrame을 저장합니다 (JSONL 또는 CSV).
    DATA_FORMAT 환경 변수에 따라 형식을 결정합니다.
    
    Args:
        df: 저장할 DataFrame
        chart_date: 수집 날짜
        sort_key: 정렬 키 (None이면 기본 파일명)
    """
    data_format = get_data_format()
    if data_format == 'jsonl':
        save_fact_weekly_chart_jsonl(df, chart_date, sort_key)
    else:
        save_fact_weekly_chart_csv(df, chart_date)


def transform_parsed_data_to_models(
    parsed_data: List[Dict[str, any]],
    chart_date: date,
    sort_key: Optional[str] = None
) -> tuple[List[Dict], List[Dict]]:
    """
    파싱된 데이터를 모델 스키마에 맞게 변환합니다.
    
    실제 수집되는 필드에 따라 이 함수를 수정해야 할 수 있습니다.
    
    Args:
        parsed_data: 파싱된 웹툰 차트 데이터 리스트
        chart_date: 수집 날짜
    
    Returns:
        (dim_webtoon_records, fact_weekly_chart_records) 튜플
    """
    dim_records = []
    fact_records = []
    
    for item in parsed_data:
        try:
            # dim_webtoon 레코드 생성
            # 카카오 웹툰 API에서 수집 가능한 모든 필드 포함
            dim_record = create_dim_webtoon_record(
                webtoon_id=item.get('webtoon_id', ''),
                title=item.get('title', ''),
                author=item.get('author'),  # 선택적 필드 (차트 API에서 수집)
                genre=item.get('genre'),    # 선택적 필드 (card.genreFilters에서 수집)
                tags=item.get('tags'),      # 선택적 필드 (content.seoKeywords에서 수집)
                seo_id=item.get('seo_id'),  # 선택적 필드 (content.seoId)
                adult=item.get('adult'),     # 선택적 필드 (content.adult)
                catchphrase=item.get('catchphrase'),  # 선택적 필드 (content.catchphraseTwoLines)
                badges=item.get('badges'),   # 선택적 필드 (content.badges의 title)
                content_id=item.get('content_id'),  # 선택적 필드 (content.id)
            )
            
            if validate_dim_webtoon_record(dim_record):
                dim_records.append(dim_record)
            else:
                logger.warning(f"dim_webtoon 레코드 검증 실패: {item}")
                continue
            
            # fact_weekly_chart 레코드 생성
            # collected_at은 자동으로 현재 시각이 설정됨
            fact_record = create_fact_weekly_chart_record(
                chart_date=chart_date,
                webtoon_id=item.get('webtoon_id', ''),
                rank=item.get('rank', 0),
                weekday=item.get('weekday'),  # 요일 정보
                view_count=item.get('view_count'),  # 조회수 (있는 경우)
                sort_key=item.get('_sort_key') or sort_key,  # 정렬 키
                # year, month, week는 collected_at에서 자동 계산됨
            )
            
            if validate_fact_weekly_chart_record(fact_record):
                fact_records.append(fact_record)
            else:
                logger.warning(f"fact_weekly_chart 레코드 검증 실패: {item}")
                continue
                
        except Exception as e:
            logger.error(f"데이터 변환 실패: {item}, 오류: {e}")
            continue
    
    logger.info(f"데이터 변환 완료: dim_webtoon {len(dim_records)}개, fact_weekly_chart {len(fact_records)}개")
    return dim_records, fact_records


def merge_dim_webtoon(
    existing_df: pd.DataFrame,
    new_records: List[Dict]
) -> pd.DataFrame:
    """
    새로운 dim_webtoon 레코드를 기존 데이터와 병합합니다.
    중복된 webtoon_id는 업데이트합니다.
    
    Args:
        existing_df: 기존 dim_webtoon DataFrame
        new_records: 새로운 레코드 리스트
    
    Returns:
        병합된 DataFrame
    """
    if len(new_records) == 0:
        return existing_df
    
    new_df = pd.DataFrame(new_records)
    
    if len(existing_df) == 0:
        return new_df
    
    # 모든 레코드를 합치고, webtoon_id 기준으로 중복 제거 (최신 것만 유지)
    # updated_at이 최신인 것을 유지하도록 정렬
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    
    # updated_at을 datetime으로 변환
    combined_df['updated_at'] = pd.to_datetime(combined_df['updated_at'])
    
    # webtoon_id 기준으로 정렬 (updated_at 최신순)
    combined_df = combined_df.sort_values('updated_at', ascending=False)
    
    # webtoon_id 기준으로 중복 제거 (첫 번째 것만 유지 = 최신 것)
    combined_df = combined_df.drop_duplicates(subset=['webtoon_id'], keep='first')
    
    # updated_at을 다시 문자열로 변환
    combined_df['updated_at'] = combined_df['updated_at'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    combined_df['created_at'] = pd.to_datetime(combined_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    
    return combined_df.reset_index(drop=True)


def merge_fact_weekly_chart(
    existing_df: pd.DataFrame,
    new_records: List[Dict],
    chart_date: date
) -> pd.DataFrame:
    """
    새로운 fact_weekly_chart 레코드를 기존 데이터와 병합합니다.
    같은 날짜의 중복 레코드는 제거합니다 (멱등성 보장).
    
    주의: 같은 날짜에 같은 웹툰이 여러 요일에 나타날 수 있으므로,
    (chart_date, webtoon_id, weekday) 조합으로 중복을 체크합니다.
    weekday가 None인 경우 (chart_date, webtoon_id)로 체크합니다.
    
    Args:
        existing_df: 기존 fact_weekly_chart DataFrame
        new_records: 새로운 레코드 리스트
        chart_date: 수집 날짜
    
    Returns:
        병합된 DataFrame
    """
    if len(new_records) == 0:
        return existing_df
    
    new_df = pd.DataFrame(new_records)
    
    # 기존 레코드가 있으면 중복 체크
    if len(existing_df) > 0:
        # (chart_date, webtoon_id, weekday) 조합으로 중복 체크
        # weekday가 None인 경우도 고려
        existing_df['weekday'] = existing_df['weekday'].fillna('')
        new_df['weekday'] = new_df['weekday'].fillna('')
        
        # 기존 레코드의 (chart_date, webtoon_id, weekday) 조합 집합
        existing_combos = set(
            zip(
                existing_df['chart_date'].astype(str),
                existing_df['webtoon_id'].astype(str),
                existing_df['weekday'].astype(str)
            )
        )
        
        # 새로운 레코드의 (chart_date, webtoon_id, weekday) 조합
        new_combos = list(
            zip(
                new_df['chart_date'].astype(str),
                new_df['webtoon_id'].astype(str),
                new_df['weekday'].astype(str)
            )
        )
        
        # 중복되지 않은 레코드만 필터링
        new_df_filtered = new_df[
            [combo not in existing_combos for combo in new_combos]
        ]
        
        if len(new_df_filtered) > 0:
            removed_count = len(new_df) - len(new_df_filtered)
            logger.info(f"중복 제거: {removed_count}개 중복 레코드 제거됨 (남은 레코드: {len(new_df_filtered)}개)")
            return pd.concat([existing_df, new_df_filtered], ignore_index=True)
        else:
            logger.info(f"모든 레코드가 중복입니다. 데이터 변경 없음.")
            return existing_df
    else:
        # 기존 레코드가 없으면 그대로 추가
        return new_df


def transform_and_save(
    parsed_data: List[Dict[str, any]],
    chart_date: date,
    sort_key: Optional[str] = None
) -> bool:
    """
    파싱된 데이터를 변환하여 CSV로 저장합니다.
    멱등성을 보장합니다.
    
    Args:
        parsed_data: 파싱된 웹툰 차트 데이터 리스트
        chart_date: 수집 날짜
        sort_key: 정렬 키 (None이면 기본 파일명)
    
    Returns:
        성공 여부
    """
    try:
        # 1. 파싱된 데이터를 모델로 변환
        dim_records, fact_records = transform_parsed_data_to_models(parsed_data, chart_date, sort_key)
        
        if len(dim_records) == 0 and len(fact_records) == 0:
            logger.warning("변환된 레코드가 없습니다.")
            return False
        
        # 2. 기존 데이터 로드
        existing_dim_df = load_dim_webtoon()
        existing_fact_df = load_fact_weekly_chart(chart_date)
        
        # 3. Foreign Key 검증
        existing_webtoon_ids = set(existing_dim_df['webtoon_id'].astype(str)) if len(existing_dim_df) > 0 else set()
        new_webtoon_ids = {r['webtoon_id'] for r in dim_records}
        all_webtoon_ids = existing_webtoon_ids | new_webtoon_ids
        
        # fact_records의 webtoon_id가 모두 존재하는지 확인
        invalid_facts = [
            r for r in fact_records
            if r['webtoon_id'] not in all_webtoon_ids
        ]
        if invalid_facts:
            logger.warning(f"Foreign Key 검증 실패: {len(invalid_facts)}개 레코드의 webtoon_id가 dim_webtoon에 없습니다.")
            # 일단 경고만 하고 진행 (dim_webtoon에 추가될 예정)
        
        # 4. 데이터 병합 (멱등성 보장)
        merged_dim_df = merge_dim_webtoon(existing_dim_df, dim_records)
        merged_fact_df = merge_fact_weekly_chart(existing_fact_df, fact_records, chart_date)
        
        # 5. CSV 저장
        save_dim_webtoon(merged_dim_df)
        save_fact_weekly_chart(merged_fact_df, chart_date, sort_key)
        
        logger.info(f"데이터 변환 및 저장 완료: chart_date={format_date(chart_date)}")
        return True
        
    except Exception as e:
        logger.error(f"데이터 변환 및 저장 실패: {e}")
        raise


if __name__ == "__main__":
    # 테스트 실행
    from src.utils import setup_logging
    
    setup_logging()
    
    # 예시 데이터로 테스트
    test_data = [
        {'rank': 1, 'title': '테스트 웹툰 1', 'webtoon_id': '123456'},
        {'rank': 2, 'title': '테스트 웹툰 2', 'webtoon_id': '789012'},
    ]
    
    result = transform_and_save(test_data, date.today())
    print(f"변환 및 저장 결과: {'성공' if result else '실패'}")
