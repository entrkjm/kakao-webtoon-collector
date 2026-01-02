"""
BigQuery 업로드 모듈

JSONL 파일을 BigQuery에 적재하는 기능을 제공합니다.
- dim_webtoon 업로드 (MERGE로 멱등성 보장)
- fact_weekly_chart 업로드 (MERGE로 멱등성 보장)
"""

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.auth import default as default_auth
import subprocess

from src.utils import (
    get_dim_webtoon_jsonl_path,
    get_chart_jsonl_path,
    setup_logging,
)

logger = logging.getLogger(__name__)


# BigQuery 설정 (환경 변수 또는 기본값)
BIGQUERY_PROJECT_ID = os.getenv('BIGQUERY_PROJECT_ID', 'kakao-webtoon-collector')
BIGQUERY_DATASET_ID = os.getenv('BIGQUERY_DATASET_ID', 'kakao_webtoon')


def get_bigquery_client() -> bigquery.Client:
    """
    BigQuery 클라이언트를 생성합니다.
    ADC가 없으면 gcloud 인증을 사용합니다.
    
    Returns:
        BigQuery 클라이언트 객체
    """
    try:
        # 먼저 ADC 시도
        credentials, project = default_auth()
        return bigquery.Client(project=BIGQUERY_PROJECT_ID, credentials=credentials)
    except Exception as e:
        logger.warning(f"ADC 인증 실패, gcloud 인증 사용 시도: {e}")
        # gcloud 인증 사용
        try:
            account_result = subprocess.run(
                ['gcloud', 'config', 'get-value', 'account'],
                capture_output=True,
                text=True,
                check=True
            )
            account = account_result.stdout.strip()
            logger.info(f"gcloud 계정 사용: {account}")
            
            return bigquery.Client(project=BIGQUERY_PROJECT_ID)
        except Exception as e2:
            logger.error(f"gcloud 인증도 실패: {e2}")
            raise Exception("BigQuery 인증 실패. 'gcloud auth application-default login'을 실행하세요.")


def load_jsonl_file(file_path: Path) -> List[Dict]:
    """
    JSONL 파일을 읽어서 레코드 리스트로 반환합니다.
    
    Args:
        file_path: JSONL 파일 경로
    
    Returns:
        레코드 리스트
    """
    if not file_path.exists():
        logger.warning(f"파일이 존재하지 않습니다: {file_path}")
        return []
    
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 파싱 오류 (라인 {line_num}): {e}")
                        continue
    except Exception as e:
        logger.error(f"파일 읽기 오류: {e}")
        return []
    
    logger.info(f"JSONL 파일 로드 완료: {len(records)}개 레코드 ({file_path})")
    return records


def upload_dim_webtoon(jsonl_path: Optional[Path] = None, dry_run: bool = False) -> bool:
    """
    dim_webtoon JSONL 파일을 BigQuery에 업로드합니다.
    
    Args:
        jsonl_path: JSONL 파일 경로 (None이면 기본 경로 사용)
        dry_run: True이면 실제 업로드하지 않고 검증만 수행
    
    Returns:
        성공 여부
    """
    if jsonl_path is None:
        jsonl_path = get_dim_webtoon_jsonl_path()
    
    records = load_jsonl_file(jsonl_path)
    if len(records) == 0:
        logger.warning("업로드할 레코드가 없습니다.")
        return True
    
    if dry_run:
        logger.info(f"[DRY RUN] dim_webtoon 업로드 예정: {len(records)}개 레코드")
        return True
    
    try:
        client = get_bigquery_client()
        table_id = f"{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.dim_webtoon"
        
        # 데이터 변환 및 정규화
        for record in records:
            # webtoon_id를 문자열로 보장
            if 'webtoon_id' in record:
                record['webtoon_id'] = str(record['webtoon_id'])
            
            # tags를 ARRAY로 변환 (이미 리스트면 그대로 사용)
            if 'tags' in record and record['tags']:
                if isinstance(record['tags'], str):
                    # 파이프로 구분된 문자열을 리스트로 변환
                    record['tags'] = [t.strip() for t in record['tags'].split('|') if t.strip()]
                elif not isinstance(record['tags'], list):
                    record['tags'] = []
            else:
                record['tags'] = None
            
            # badges를 ARRAY로 변환 (이미 리스트면 그대로 사용)
            if 'badges' in record and record['badges']:
                if isinstance(record['badges'], str):
                    # 파이프로 구분된 문자열을 리스트로 변환
                    record['badges'] = [b.strip() for b in record['badges'].split('|') if b.strip()]
                elif not isinstance(record['badges'], list):
                    record['badges'] = []
            else:
                record['badges'] = None
            
            # content_id를 정수로 변환
            if 'content_id' in record and record['content_id'] is not None:
                try:
                    record['content_id'] = int(record['content_id'])
                except (ValueError, TypeError):
                    record['content_id'] = None
            
            # adult를 boolean으로 변환
            if 'adult' in record and record['adult'] is not None:
                record['adult'] = bool(record['adult'])
            
            # datetime 객체를 ISO 형식 문자열로 변환
            if 'created_at' in record and record['created_at']:
                if isinstance(record['created_at'], datetime):
                    record['created_at'] = record['created_at'].isoformat()
            if 'updated_at' in record and record['updated_at']:
                if isinstance(record['updated_at'], datetime):
                    record['updated_at'] = record['updated_at'].isoformat()
        
        # 임시 테이블에 먼저 업로드
        temp_table_id = f"{table_id}_temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 스키마 정의 (tags와 badges를 REPEATED STRING으로 명시)
        schema = [
            bigquery.SchemaField("webtoon_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("author", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("genre", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
            bigquery.SchemaField("seo_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("adult", "BOOLEAN", mode="NULLABLE"),
            bigquery.SchemaField("catchphrase", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("badges", "STRING", mode="REPEATED"),
            bigquery.SchemaField("content_id", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        # 배치로 업로드 (한 번에 최대 1000개씩)
        batch_size = 1000
        total_uploaded = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            job = client.load_table_from_json(
                batch,
                temp_table_id,
                job_config=bigquery.LoadJobConfig(
                    schema=schema,
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND if i > 0 else bigquery.WriteDisposition.WRITE_TRUNCATE,
                    create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
                    ignore_unknown_values=False,
                )
            )
            
            job.result()  # 작업 완료 대기
            total_uploaded += len(batch)
            logger.info(f"dim_webtoon 임시 테이블 업로드 진행: {total_uploaded}/{len(records)}")
        
        # MERGE 문으로 중복 제거 및 업데이트
        merge_query = f"""
        MERGE `{table_id}` AS target
        USING (
            SELECT 
                CAST(webtoon_id AS STRING) AS webtoon_id,
                title,
                author,
                genre,
                tags,
                seo_id,
                CAST(adult AS BOOLEAN) AS adult,
                catchphrase,
                badges,
                CAST(content_id AS INT64) AS content_id,
                CAST(created_at AS TIMESTAMP) AS created_at,
                CAST(updated_at AS TIMESTAMP) AS updated_at
            FROM (
                SELECT 
                    *,
                    ROW_NUMBER() OVER (PARTITION BY CAST(webtoon_id AS STRING) ORDER BY CAST(updated_at AS TIMESTAMP) DESC) AS rn
                FROM `{temp_table_id}`
            )
            WHERE rn = 1
        ) AS source
        ON target.webtoon_id = source.webtoon_id
        WHEN MATCHED THEN
            UPDATE SET
                title = source.title,
                author = source.author,
                genre = source.genre,
                tags = source.tags,
                seo_id = source.seo_id,
                adult = source.adult,
                catchphrase = source.catchphrase,
                badges = source.badges,
                content_id = source.content_id,
                updated_at = source.updated_at
        WHEN NOT MATCHED THEN
            INSERT (webtoon_id, title, author, genre, tags, seo_id, adult, catchphrase, badges, content_id, created_at, updated_at)
            VALUES (source.webtoon_id, source.title, source.author, source.genre, source.tags, source.seo_id, source.adult, source.catchphrase, source.badges, source.content_id, source.created_at, source.updated_at)
        """
        
        client.query(merge_query).result()
        logger.info(f"✅ dim_webtoon MERGE 완료")
        
        # 임시 테이블 삭제
        client.delete_table(temp_table_id, not_found_ok=True)
        
        logger.info(f"✅ dim_webtoon 업로드 완료: {total_uploaded}개 레코드")
        return True
        
    except Exception as e:
        logger.error(f"❌ dim_webtoon 업로드 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def upload_fact_weekly_chart(
    chart_date: date,
    sort_key: Optional[str] = None,
    jsonl_path: Optional[Path] = None,
    dry_run: bool = False
) -> bool:
    """
    fact_weekly_chart JSONL 파일을 BigQuery에 업로드합니다.
    
    Args:
        chart_date: 차트 날짜
        sort_key: 정렬 키 (None이면 기본값)
        jsonl_path: JSONL 파일 경로 (None이면 기본 경로 사용)
        dry_run: True이면 실제 업로드하지 않고 검증만 수행
    
    Returns:
        성공 여부
    """
    if jsonl_path is None:
        jsonl_path = get_chart_jsonl_path(chart_date, sort_key)
    
    records = load_jsonl_file(jsonl_path)
    if len(records) == 0:
        logger.warning(f"업로드할 레코드가 없습니다: {jsonl_path}")
        return True
    
    if dry_run:
        logger.info(f"[DRY RUN] fact_weekly_chart 업로드 예정: {len(records)}개 레코드")
        return True
    
    try:
        client = get_bigquery_client()
        table_id = f"{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.fact_weekly_chart"
        
        # 데이터 변환 및 정규화
        for record in records:
            # webtoon_id를 문자열로 보장
            if 'webtoon_id' in record:
                record['webtoon_id'] = str(record['webtoon_id'])
            
            # datetime 객체를 문자열로 변환
            if 'chart_date' in record and record['chart_date']:
                if isinstance(record['chart_date'], date):
                    record['chart_date'] = record['chart_date'].isoformat()
                elif isinstance(record['chart_date'], datetime):
                    record['chart_date'] = record['chart_date'].date().isoformat()
            if 'collected_at' in record and record['collected_at']:
                if isinstance(record['collected_at'], datetime):
                    record['collected_at'] = record['collected_at'].isoformat()
            
            # view_count를 정수로 변환
            if 'view_count' in record and record['view_count'] is not None:
                try:
                    if isinstance(record['view_count'], str):
                        record['view_count'] = int(record['view_count']) if record['view_count'].strip() else None
                    elif isinstance(record['view_count'], (int, float)):
                        record['view_count'] = int(record['view_count'])
                except (ValueError, TypeError):
                    record['view_count'] = None
            
            # rank를 정수로 보장
            if 'rank' in record and record['rank'] is not None:
                try:
                    if isinstance(record['rank'], str):
                        record['rank'] = int(record['rank'])
                    elif isinstance(record['rank'], (int, float)):
                        record['rank'] = int(record['rank'])
                except (ValueError, TypeError):
                    logger.warning(f"rank 변환 실패: {record.get('rank')}")
            
            # year, month, week를 정수로 보장
            for field in ['year', 'month', 'week']:
                if field in record and record[field] is not None:
                    try:
                        if isinstance(record[field], str):
                            record[field] = int(record[field])
                        elif isinstance(record[field], (int, float)):
                            record[field] = int(record[field])
                    except (ValueError, TypeError):
                        logger.warning(f"{field} 변환 실패: {record.get(field)}")
        
        # 임시 테이블에 먼저 업로드
        temp_table_id = f"{table_id}_temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        batch_size = 1000
        total_uploaded = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            job = client.load_table_from_json(
                batch,
                temp_table_id,
                job_config=bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND if i > 0 else bigquery.WriteDisposition.WRITE_TRUNCATE,
                    create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
                    ignore_unknown_values=False,
                )
            )
            
            job.result()
            total_uploaded += len(batch)
            logger.info(f"fact_weekly_chart 임시 테이블 업로드 진행: {total_uploaded}/{len(records)}")
        
        # MERGE 실행 (chart_date와 webtoon_id 조합이 고유해야 함)
        # sort_key 정보도 고려 (같은 날짜, 같은 웹툰, 같은 정렬 키는 중복)
        # sort_key 컬럼이 있는지 확인
        temp_table = client.get_table(temp_table_id)
        has_sort_key = any(field.name == 'sort_key' for field in temp_table.schema)
        
        if has_sort_key:
            merge_query = f"""
            MERGE `{table_id}` AS target
            USING (
                SELECT 
                    CAST(chart_date AS DATE) AS chart_date,
                    CAST(webtoon_id AS STRING) AS webtoon_id,
                    rank,
                    CAST(collected_at AS TIMESTAMP) AS collected_at,
                    weekday,
                    CAST(year AS INT64) AS year,
                    CAST(month AS INT64) AS month,
                    CAST(week AS INT64) AS week,
                    CAST(view_count AS INT64) AS view_count,
                    sort_key
                FROM `{temp_table_id}`
            ) AS source
            ON target.chart_date = source.chart_date 
                AND target.webtoon_id = source.webtoon_id 
                AND COALESCE(target.sort_key, '') = COALESCE(source.sort_key, '')
            WHEN NOT MATCHED THEN
                INSERT (chart_date, webtoon_id, rank, collected_at, weekday, year, month, week, view_count, sort_key)
                VALUES (source.chart_date, source.webtoon_id, source.rank, source.collected_at, source.weekday, source.year, source.month, source.week, source.view_count, source.sort_key)
            """
        else:
            # sort_key 컬럼이 없으면 기존 방식 사용
            merge_query = f"""
            MERGE `{table_id}` AS target
            USING (
                SELECT 
                    CAST(chart_date AS DATE) AS chart_date,
                    CAST(webtoon_id AS STRING) AS webtoon_id,
                    rank,
                    CAST(collected_at AS TIMESTAMP) AS collected_at,
                    weekday,
                    CAST(year AS INT64) AS year,
                    CAST(month AS INT64) AS month,
                    CAST(week AS INT64) AS week,
                    CAST(view_count AS INT64) AS view_count
                FROM `{temp_table_id}`
            ) AS source
            ON target.chart_date = source.chart_date 
                AND target.webtoon_id = source.webtoon_id
            WHEN NOT MATCHED THEN
                INSERT (chart_date, webtoon_id, rank, collected_at, weekday, year, month, week, view_count)
                VALUES (source.chart_date, source.webtoon_id, source.rank, source.collected_at, source.weekday, source.year, source.month, source.week, source.view_count)
            """
        
        client.query(merge_query).result()
        client.delete_table(temp_table_id, not_found_ok=True)
        
        logger.info(f"✅ fact_weekly_chart 업로드 완료: {total_uploaded}개 레코드")
        return True
        
    except Exception as e:
        logger.error(f"❌ fact_weekly_chart 업로드 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

