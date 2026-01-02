"""
유틸리티 함수

공통으로 사용되는 유틸리티 함수들을 모아둡니다.
- 날짜 처리
- 파일 I/O
- 로깅 설정
등
"""

import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional


def setup_logging(level: int = logging.INFO, log_file: Optional[Path] = None) -> None:
    """
    로깅 설정을 초기화합니다.
    콘솔과 파일(선택) 모두에 로그를 출력합니다.
    
    Args:
        level: 로그 레벨 (기본값: INFO)
        log_file: 로그 파일 경로 (None이면 파일 로그 없음)
    """
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    root_logger.setLevel(level)


def get_data_dir() -> Path:
    """
    데이터 디렉토리 경로를 반환합니다.
    환경 변수 DATA_DIR이 설정되어 있으면 그 값을 사용합니다.
    
    Returns:
        data 디렉토리 Path 객체
    """
    data_dir_env = os.getenv('DATA_DIR')
    if data_dir_env:
        return Path(data_dir_env)
    
    project_root = Path(__file__).parent.parent
    return project_root / 'data'


def get_raw_html_dir(chart_date: Optional[date] = None) -> Path:
    """
    HTML 원본 저장 디렉토리 경로를 반환합니다.
    
    Args:
        chart_date: 수집 날짜 (없으면 날짜별 디렉토리 생성 안 함)
    
    Returns:
        raw HTML 디렉토리 Path 객체
    """
    data_dir = get_data_dir()
    raw_dir = data_dir / 'raw'
    
    if chart_date:
        date_dir = raw_dir / chart_date.strftime('%Y-%m-%d')
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir
    
    return raw_dir


def get_processed_dir() -> Path:
    """
    정제된 데이터 저장 디렉토리 경로를 반환합니다.
    
    Returns:
        processed 디렉토리 Path 객체
    """
    data_dir = get_data_dir()
    processed_dir = data_dir / 'processed'
    processed_dir.mkdir(parents=True, exist_ok=True)
    return processed_dir


def get_chart_csv_path(chart_date: date) -> Path:
    """
    주간 차트 CSV 파일 경로를 반환합니다 (날짜별 파일).
    
    Args:
        chart_date: 수집 날짜
    
    Returns:
        CSV 파일 Path 객체
    """
    processed_dir = get_processed_dir()
    chart_dir = processed_dir / 'fact_weekly_chart'
    chart_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{chart_date.strftime('%Y-%m-%d')}.csv"
    return chart_dir / filename


def get_dim_webtoon_csv_path() -> Path:
    """
    dim_webtoon CSV 파일 경로를 반환합니다.
    
    Returns:
        CSV 파일 Path 객체
    """
    processed_dir = get_processed_dir()
    return processed_dir / 'dim_webtoon.csv'


def get_data_format() -> str:
    """
    데이터 저장 형식을 반환합니다.
    환경 변수 DATA_FORMAT이 설정되어 있으면 그 값을 사용하고,
    없으면 기본값 'jsonl'을 반환합니다.
    
    Returns:
        'jsonl' 또는 'csv'
    """
    return os.getenv('DATA_FORMAT', 'jsonl').lower()


def get_chart_jsonl_path(chart_date: date, sort_key: Optional[str] = None) -> Path:
    """
    주간 차트 JSONL 파일 경로를 반환합니다 (날짜별 파일).
    
    Args:
        chart_date: 수집 날짜
        sort_key: 정렬 키 (선택사항)
    
    Returns:
        JSONL 파일 Path 객체
    """
    processed_dir = get_processed_dir()
    chart_dir = processed_dir / 'fact_weekly_chart'
    chart_dir.mkdir(parents=True, exist_ok=True)
    
    if sort_key:
        filename = f"{chart_date.strftime('%Y-%m-%d')}_{sort_key}.jsonl"
    else:
        filename = f"{chart_date.strftime('%Y-%m-%d')}.jsonl"
    
    return chart_dir / filename


def get_dim_webtoon_jsonl_path() -> Path:
    """
    dim_webtoon JSONL 파일 경로를 반환합니다.
    
    Returns:
        JSONL 파일 Path 객체
    """
    processed_dir = get_processed_dir()
    return processed_dir / 'dim_webtoon.jsonl'


def get_logs_dir() -> Path:
    """
    로그 파일 저장 디렉토리 경로를 반환합니다.
    
    Returns:
        logs 디렉토리 Path 객체
    """
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_log_file_path(suffix: Optional[str] = None) -> Path:
    """
    로그 파일 경로를 생성합니다.
    
    Args:
        suffix: 파일명 접미사 (예: "pipeline")
    
    Returns:
        로그 파일 Path 객체
    """
    logs_dir = get_logs_dir()
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    if suffix:
        filename = f"{suffix}_{timestamp}.log"
    else:
        filename = f"{timestamp}.log"
    
    return logs_dir / filename


def ensure_dir(path: Path) -> None:
    """
    디렉토리가 존재하지 않으면 생성합니다.
    
    Args:
        path: 디렉토리 경로
    """
    path.mkdir(parents=True, exist_ok=True)


def format_datetime(dt: datetime) -> str:
    """
    datetime을 CSV 저장용 문자열로 변환합니다.
    
    Args:
        dt: datetime 객체
    
    Returns:
        ISO 형식 문자열 (YYYY-MM-DD HH:MM:SS)
    """
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def parse_datetime(dt_str: str) -> datetime:
    """
    CSV에서 읽은 datetime 문자열을 datetime 객체로 변환합니다.
    
    Args:
        dt_str: datetime 문자열
    
    Returns:
        datetime 객체
    """
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return datetime.fromisoformat(dt_str.replace(' ', 'T'))


def format_date(d: date) -> str:
    """
    date를 CSV 저장용 문자열로 변환합니다.
    
    Args:
        d: date 객체
    
    Returns:
        ISO 형식 문자열 (YYYY-MM-DD)
    """
    return d.strftime('%Y-%m-%d')


def parse_date(date_str: str) -> date:
    """
    CSV에서 읽은 date 문자열을 date 객체로 변환합니다.
    
    Args:
        date_str: date 문자열
    
    Returns:
        date 객체
    """
    return datetime.strptime(date_str, '%Y-%m-%d').date()

