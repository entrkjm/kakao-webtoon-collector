"""
데이터 검증 Cloud Function
주기적으로 BigQuery 데이터를 확인하여 수집 실패를 감지합니다.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from google.cloud import bigquery

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 환경 변수
BIGQUERY_PROJECT_ID = os.environ.get("BIGQUERY_PROJECT_ID", "kakao-webtoon-collector")
BIGQUERY_DATASET_ID = os.environ.get("BIGQUERY_DATASET_ID", "kakao_webtoon")
MIN_EXPECTED_RECORDS = int(os.environ.get("MIN_EXPECTED_RECORDS", "500"))  # 최소 예상 레코드 수 (기본값: 500)
NOTIFICATION_CHANNEL_EMAIL = os.environ.get("NOTIFICATION_CHANNEL_EMAIL", "")


def get_bigquery_client():
    """BigQuery 클라이언트 생성"""
    return bigquery.Client(project=BIGQUERY_PROJECT_ID)


def check_data_collection(date_str: str = None) -> Dict[str, Any]:
    """
    데이터 수집 상태를 확인합니다.
    
    Args:
        date_str: 확인할 날짜 (YYYY-MM-DD 형식, None이면 오늘)
    
    Returns:
        검증 결과 딕셔너리
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    client = get_bigquery_client()
    
    results = {
        "date": date_str,
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "all_passed": True,
        "errors": []
    }
    
    try:
        # 1. fact_weekly_chart 확인
        chart_query = f"""
        SELECT 
            COUNT(*) AS total_records,
            COUNT(DISTINCT webtoon_id) AS unique_webtoons,
            COUNT(DISTINCT weekday) AS weekday_count,
            COUNT(DISTINCT sort_key) AS sort_key_count,
            COUNTIF(weekday IS NULL) AS null_weekday_count,
            COUNTIF(sort_key IS NULL) AS null_sort_key_count,
            COUNTIF(view_count IS NULL) AS null_view_count_count
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.fact_weekly_chart`
        WHERE chart_date = '{date_str}'
        """
        
        chart_job = client.query(chart_query)
        chart_results = list(chart_job.result())
        
        if chart_results:
            chart_data = chart_results[0]
            chart_count = chart_data.total_records
            chart_unique = chart_data.unique_webtoons
            weekday_count = chart_data.weekday_count
            sort_key_count = chart_data.sort_key_count
            null_weekday = chart_data.null_weekday_count
            null_sort_key = chart_data.null_sort_key_count
            null_view_count = chart_data.null_view_count_count
            
            results["checks"]["fact_weekly_chart"] = {
                "total_records": chart_count,
                "unique_webtoons": chart_unique,
                "weekday_count": weekday_count,
                "sort_key_count": sort_key_count,
                "null_weekday_count": null_weekday,
                "null_sort_key_count": null_sort_key,
                "null_view_count_count": null_view_count,
                "passed": chart_count >= MIN_EXPECTED_RECORDS and null_weekday == 0 and null_sort_key == 0
            }
            
            if chart_count < MIN_EXPECTED_RECORDS:
                results["all_passed"] = False
                results["errors"].append(
                    f"fact_weekly_chart: 예상 레코드 수({MIN_EXPECTED_RECORDS})보다 적습니다. "
                    f"실제: {chart_count}개"
                )
            
            if null_weekday > 0:
                results["all_passed"] = False
                results["errors"].append(
                    f"fact_weekly_chart: weekday가 NULL인 레코드가 {null_weekday}개 있습니다."
                )
            
            if null_sort_key > 0:
                results["all_passed"] = False
                results["errors"].append(
                    f"fact_weekly_chart: sort_key가 NULL인 레코드가 {null_sort_key}개 있습니다."
                )
        else:
            results["all_passed"] = False
            results["checks"]["fact_weekly_chart"] = {
                "total_records": 0,
                "unique_webtoons": 0,
                "weekday_count": 0,
                "sort_key_count": 0,
                "null_weekday_count": 0,
                "null_sort_key_count": 0,
                "null_view_count_count": 0,
                "passed": False
            }
            results["errors"].append(f"fact_weekly_chart: {date_str} 데이터가 없습니다.")
        
        # 2. dim_webtoon 확인 (Foreign Key 관계 검증)
        dim_query = f"""
        SELECT COUNT(*) AS total_webtoons
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.dim_webtoon`
        """
        
        dim_job = client.query(dim_query)
        dim_results = list(dim_job.result())
        
        if dim_results:
            dim_count = dim_results[0].total_webtoons
            results["checks"]["dim_webtoon"] = {
                "total_webtoons": dim_count,
                "passed": dim_count > 0
            }
            
            if dim_count == 0:
                results["all_passed"] = False
                results["errors"].append("dim_webtoon: 웹툰 데이터가 없습니다.")
        else:
            results["all_passed"] = False
            results["checks"]["dim_webtoon"] = {
                "total_webtoons": 0,
                "passed": False
            }
            results["errors"].append("dim_webtoon: 데이터가 없습니다.")
        
        # 3. Foreign Key 관계 검증 (fact_weekly_chart의 webtoon_id가 dim_webtoon에 존재하는지)
        fk_query = f"""
        SELECT COUNT(*) AS orphan_records
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.fact_weekly_chart` f
        LEFT JOIN `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.dim_webtoon` d
        ON f.webtoon_id = d.webtoon_id
        WHERE f.chart_date = '{date_str}' AND d.webtoon_id IS NULL
        """
        
        fk_job = client.query(fk_query)
        fk_results = list(fk_job.result())
        
        if fk_results:
            orphan_count = fk_results[0].orphan_records
            results["checks"]["foreign_key"] = {
                "orphan_records": orphan_count,
                "passed": orphan_count == 0
            }
            
            if orphan_count > 0:
                results["all_passed"] = False
                results["errors"].append(
                    f"Foreign Key 검증 실패: dim_webtoon에 없는 webtoon_id가 {orphan_count}개 있습니다."
                )
        
        # 4. 최근 수집 시간 확인 (24시간 이내에 수집되었는지)
        recent_query = f"""
        SELECT 
            MAX(collected_at) AS last_collected
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.fact_weekly_chart`
        WHERE chart_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
        """
        
        recent_job = client.query(recent_query)
        recent_results = list(recent_job.result())
        
        if recent_results and recent_results[0].last_collected:
            last_collected = recent_results[0].last_collected
            if isinstance(last_collected, str):
                last_collected = datetime.fromisoformat(last_collected.replace('Z', '+00:00'))
            
            hours_ago = (datetime.now(last_collected.tzinfo) - last_collected).total_seconds() / 3600
            
            results["checks"]["recent_collection"] = {
                "last_collected": str(last_collected),
                "hours_ago": round(hours_ago, 2),
                "passed": hours_ago < 48  # 48시간 이내에 수집되었는지
            }
            
            if hours_ago >= 48:
                results["all_passed"] = False
                results["errors"].append(
                    f"최근 수집 시간: {round(hours_ago, 2)}시간 전 "
                    f"(마지막 수집: {last_collected})"
                )
        else:
            results["all_passed"] = False
            results["checks"]["recent_collection"] = {
                "last_collected": None,
                "hours_ago": None,
                "passed": False
            }
            results["errors"].append("최근 2일 이내 데이터 수집 기록이 없습니다.")
        
    except Exception as e:
        logger.error(f"데이터 검증 중 오류 발생: {e}", exc_info=True)
        results["all_passed"] = False
        results["errors"].append(f"검증 중 오류 발생: {str(e)}")
    
    return results


def send_alert(message: str, subject: str = "파이프라인 데이터 수집 실패 알림"):
    """
    알림을 전송합니다.
    
    Args:
        message: 알림 메시지
        subject: 알림 제목
    """
    if not NOTIFICATION_CHANNEL_EMAIL:
        logger.warning("NOTIFICATION_CHANNEL_EMAIL이 설정되지 않아 알림을 전송할 수 없습니다.")
        return
    
    try:
        # Cloud Monitoring API를 사용하여 알림 전송
        # 또는 간단하게 로그에 기록 (Cloud Logging이 자동으로 알림 전송)
        logger.error(f"🚨 {subject}: {message}")
        
        # TODO: 실제 이메일 전송 로직 구현 (SendGrid, Mailgun 등 사용)
        # 현재는 Cloud Logging을 통해 알림이 전송되도록 함
        
    except Exception as e:
        logger.error(f"알림 전송 실패: {e}", exc_info=True)


def main(request):
    """
    Cloud Function 진입점
    
    Args:
        request: HTTP 요청 객체
    """
    try:
        # 요청에서 날짜 파라미터 추출 (선택사항)
        if request.method == "POST":
            request_json = request.get_json(silent=True) or {}
            date_str = request_json.get("date")
        else:
            date_str = request.args.get("date")
        
        logger.info(f"데이터 검증 시작: date={date_str}")
        
        # 데이터 검증 실행
        results = check_data_collection(date_str)
        
        # 결과 로깅
        logger.info(f"검증 결과: all_passed={results['all_passed']}, errors={len(results['errors'])}개")
        
        # 실패한 경우 알림 전송
        if not results["all_passed"]:
            error_message = "\n".join(results["errors"])
            send_alert(
                message=f"날짜: {results['date']}\n\n오류:\n{error_message}\n\n상세:\n{json.dumps(results, indent=2, ensure_ascii=False)}",
                subject=f"파이프라인 데이터 수집 실패 - {results['date']}"
            )
            
            return {
                "status": "failed",
                "message": "데이터 수집 실패 감지",
                "results": results
            }, 500
        else:
            logger.info("✅ 모든 검증 통과")
            return {
                "status": "success",
                "message": "데이터 수집 정상",
                "results": results
            }, 200
            
    except Exception as e:
        logger.error(f"데이터 검증 함수 실행 중 오류 발생: {e}", exc_info=True)
        send_alert(
            message=f"데이터 검증 함수 실행 중 오류 발생: {str(e)}",
            subject="파이프라인 데이터 검증 함수 오류"
        )
        return {
            "error": str(e),
            "status": "error"
        }, 500

