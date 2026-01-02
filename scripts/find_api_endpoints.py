"""
카카오 웹툰 API 엔드포인트 찾기 스크립트

이 스크립트는 Selenium을 사용하여:
1. 브라우저를 열고 카카오 웹툰 페이지 방문
2. 네트워크 요청을 모니터링하여 API 엔드포인트 찾기
3. 발견된 API를 테스트하여 데이터 수집 가능 여부 확인

사용 방법:
    # Selenium 설치 필요
    pip install selenium
    
    # ChromeDriver 필요 (자동 설치되거나 수동 설치)
    python scripts/find_api_endpoints.py
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Selenium은 선택적
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium이 설치되어 있지 않습니다. pip install selenium으로 설치하세요.")

KAKAO_WEBTOON_URL = "https://webtoon.kakao.com"


def find_api_with_selenium(url: str, wait_time: int = 10) -> List[Dict[str, Any]]:
    """
    Selenium을 사용하여 네트워크 요청을 모니터링하고 API 엔드포인트를 찾습니다.
    
    Args:
        url: 분석할 URL
        wait_time: 페이지 로딩 대기 시간 (초)
    
    Returns:
        발견된 API 엔드포인트 리스트
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 설치되어 있지 않습니다.")
        return []
    
    logger.info(f"Selenium으로 API 엔드포인트 찾기 시작: {url}")
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 헤드리스 모드
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
    
    # 네트워크 로그 활성화 (Selenium 4.x 방식)
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = None
    api_endpoints = []
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("브라우저 시작, 페이지 로딩 중...")
        
        driver.get(url)
        
        # 페이지 로딩 대기
        time.sleep(wait_time)
        
        # 추가 대기 (동적 콘텐츠 로딩)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # 네트워크 로그 수집
        logger.info("네트워크 요청 분석 중...")
        logs = driver.get_log('performance')
        
        for log in logs:
            try:
                message = json.loads(log['message'])
                method = message.get('message', {}).get('method', '')
                params = message.get('message', {}).get('params', {})
                
                # Network.responseReceived 이벤트만 처리
                if method == 'Network.responseReceived':
                    response = params.get('response', {})
                    request_url = response.get('url', '')
                    status = response.get('status', 0)
                    mime_type = response.get('mimeType', '')
                    
                    # API 엔드포인트 후보 찾기
                    if any(keyword in request_url.lower() for keyword in ['api', 'webtoon', 'chart', 'list', 'rank']):
                        # 중복 제거
                        if not any(ep['url'] == request_url for ep in api_endpoints):
                            api_endpoints.append({
                                'url': request_url,
                                'status': status,
                                'mime_type': mime_type,
                                'method': 'GET',  # 기본값
                                'headers': response.get('headers', {})
                            })
                            
            except Exception as e:
                continue
        
        # RequestWillBeSent 이벤트도 확인 (POST 요청 등)
        for log in logs:
            try:
                message = json.loads(log['message'])
                method = message.get('message', {}).get('method', '')
                params = message.get('message', {}).get('params', {})
                
                if method == 'Network.requestWillBeSent':
                    request = params.get('request', {})
                    request_url = request.get('url', '')
                    request_method = request.get('method', 'GET')
                    
                    if any(keyword in request_url.lower() for keyword in ['api', 'webtoon', 'chart', 'list', 'rank']):
                        if not any(ep['url'] == request_url for ep in api_endpoints):
                            api_endpoints.append({
                                'url': request_url,
                                'status': None,
                                'mime_type': None,
                                'method': request_method,
                                'headers': request.get('headers', {}),
                                'post_data': request.get('postData')
                            })
            except:
                continue
        
        logger.info(f"총 {len(api_endpoints)}개의 API 엔드포인트 후보 발견")
        
        return api_endpoints
        
    except Exception as e:
        logger.error(f"Selenium 실행 실패: {e}")
        logger.info("ChromeDriver가 필요합니다. 설치 방법:")
        logger.info("  macOS: brew install chromedriver")
        logger.info("  또는: https://chromedriver.chromium.org/downloads")
        return []
    finally:
        if driver:
            driver.quit()


def test_api_endpoint(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    """
    발견된 API 엔드포인트를 테스트합니다.
    
    Args:
        endpoint: API 엔드포인트 정보
    
    Returns:
        테스트 결과
    """
    url = endpoint['url']
    method = endpoint.get('method', 'GET')
    
    logger.info(f"API 테스트: {method} {url}")
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': KAKAO_WEBTOON_URL,
        })
        
        if method == 'GET':
            response = session.get(url, timeout=10)
        else:
            response = session.post(url, timeout=10)
        
        result = {
            'url': url,
            'method': method,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'content_type': response.headers.get('Content-Type', ''),
            'content_length': len(response.content),
        }
        
        # JSON 응답인 경우 파싱 시도
        if 'application/json' in result['content_type']:
            try:
                data = response.json()
                result['is_json'] = True
                result['data_keys'] = list(data.keys()) if isinstance(data, dict) else 'list'
                result['sample_data'] = str(data)[:500]  # 처음 500자만
            except:
                result['is_json'] = False
        
        return result
        
    except Exception as e:
        return {
            'url': url,
            'method': method,
            'success': False,
            'error': str(e)
        }


def save_results(api_endpoints: List[Dict[str, Any]], output_dir: Path) -> None:
    """
    발견된 API 엔드포인트를 파일로 저장합니다.
    
    Args:
        api_endpoints: API 엔드포인트 리스트
        output_dir: 출력 디렉토리
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filepath = output_dir / f"api_endpoints_{timestamp}.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(api_endpoints, f, ensure_ascii=False, indent=2)
    
    logger.info(f"API 엔드포인트 저장: {filepath}")


def main():
    """메인 함수"""
    output_dir = Path(__file__).parent.parent / 'data' / 'analysis'
    
    logger.info("=" * 60)
    logger.info("카카오 웹툰 API 엔드포인트 찾기")
    logger.info("=" * 60)
    
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 설치되어 있지 않습니다.")
        logger.info("설치 방법: pip install selenium")
        logger.info("ChromeDriver도 필요합니다: brew install chromedriver")
        return
    
    # 1. Selenium으로 API 엔드포인트 찾기
    api_endpoints = find_api_with_selenium(KAKAO_WEBTOON_URL, wait_time=10)
    
    if not api_endpoints:
        logger.warning("API 엔드포인트를 찾을 수 없습니다.")
        return
    
    # 2. 결과 저장
    save_results(api_endpoints, output_dir)
    
    # 3. 각 API 엔드포인트 테스트
    logger.info("\n" + "=" * 60)
    logger.info("API 엔드포인트 테스트")
    logger.info("=" * 60)
    
    test_results = []
    for endpoint in api_endpoints[:10]:  # 처음 10개만 테스트
        result = test_api_endpoint(endpoint)
        test_results.append(result)
        
        if result.get('success'):
            logger.info(f"✅ {result['url']} - Status: {result['status_code']}")
            if result.get('is_json'):
                logger.info(f"   JSON 응답 확인, 키: {result.get('data_keys', 'N/A')}")
        else:
            logger.warning(f"❌ {result['url']} - {result.get('error', 'Failed')}")
    
    # 테스트 결과 저장
    test_filepath = output_dir / f"api_test_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(test_filepath, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n테스트 결과 저장: {test_filepath}")
    logger.info("\n분석 완료!")


if __name__ == "__main__":
    main()

