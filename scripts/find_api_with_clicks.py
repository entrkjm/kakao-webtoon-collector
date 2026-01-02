"""
카카오 웹툰 API 엔드포인트 찾기 (버튼 클릭 포함)

이 스크립트는 Selenium을 사용하여:
1. 카카오 웹툰 페이지 방문
2. 요일별 버튼 클릭 (월, 화, 수, 목, 금, 토, 일)
3. 필터 버튼 클릭 (전체, 연재무료, 기다무 등)
4. 정렬 버튼 클릭 (최신순, 조회순, 전체인기순 등)
5. 각 클릭 후 네트워크 요청 모니터링하여 API 엔드포인트 찾기
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.error("Selenium이 설치되어 있지 않습니다.")

KAKAO_WEBTOON_URL = "https://webtoon.kakao.com"

# 요일 목록
WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

# 필터 목록
FILTERS = ['전체', '연재무료', '기다무']

# 정렬 목록 (예상)
SORT_OPTIONS = ['최신순', '조회순', '전체인기순', '남자인기순', '여자인기순']


def find_api_with_clicks(url: str, wait_time: int = 5) -> List[Dict[str, Any]]:
    """
    버튼 클릭을 포함하여 API 엔드포인트를 찾습니다.
    
    Args:
        url: 분석할 URL
        wait_time: 각 동작 후 대기 시간 (초)
    
    Returns:
        발견된 API 엔드포인트 리스트
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 설치되어 있지 않습니다.")
        return []
    
    logger.info(f"버튼 클릭을 포함한 API 엔드포인트 찾기 시작: {url}")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 헤드리스 모드
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
    
    # 네트워크 로그 활성화
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = None
    all_api_endpoints = []
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("브라우저 시작, 페이지 로딩 중...")
        
        driver.get(url)
        
        # 초기 페이지 로딩 대기
        time.sleep(wait_time * 2)
        
        # 초기 네트워크 요청 수집
        logger.info("초기 페이지 로딩 후 네트워크 요청 수집...")
        initial_apis = collect_network_requests(driver)
        all_api_endpoints.extend(initial_apis)
        logger.info(f"초기 로딩에서 {len(initial_apis)}개 API 발견")
        
        # 1. 요일별 클릭
        logger.info("\n" + "="*60)
        logger.info("요일별 버튼 클릭 시작")
        logger.info("="*60)
        
        for weekday in WEEKDAYS:
            try:
                logger.info(f"\n[{weekday}] 요일 클릭 시도...")
                
                # 요일 버튼 찾기 (HTML 구조: <li> 안에 <p> 태그)
                weekday_button = None
                selectors = [
                    f"//li[.//p[text()='{weekday}']]",  # <li> 안에 <p>가 있는 경우
                    f"//p[text()='{weekday}']",  # 직접 <p> 태그
                    f"//li[contains(., '{weekday}')]",  # <li> 안에 텍스트가 있는 경우
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        # 클릭 가능한 요소 찾기 (li 또는 p의 부모)
                        for elem in elements:
                            # li 요소이거나, p의 부모 li 요소
                            if elem.tag_name == 'li':
                                weekday_button = elem
                                break
                            elif elem.tag_name == 'p':
                                # p의 부모 li 찾기
                                try:
                                    parent_li = elem.find_element(By.XPATH, './ancestor::li[1]')
                                    if parent_li:
                                        weekday_button = parent_li
                                        break
                                except:
                                    pass
                        if weekday_button:
                            break
                    except:
                        continue
                
                if not weekday_button:
                    logger.warning(f"[{weekday}] 요일 버튼을 찾을 수 없습니다.")
                    continue
                
                # 클릭 전 네트워크 로그 초기화
                driver.get_log('performance')  # 로그 버퍼 비우기
                
                # 버튼 클릭
                driver.execute_script("arguments[0].click();", weekday_button)
                logger.info(f"[{weekday}] 요일 버튼 클릭 완료")
                
                # 클릭 후 대기
                time.sleep(wait_time)
                
                # 네트워크 요청 수집
                apis = collect_network_requests(driver, action=f"요일_{weekday}")
                all_api_endpoints.extend(apis)
                logger.info(f"[{weekday}] {len(apis)}개 API 발견")
                
            except Exception as e:
                logger.error(f"[{weekday}] 요일 클릭 실패: {e}")
                continue
        
        # 2. 필터 버튼 클릭 (첫 번째 요일에서 테스트)
        logger.info("\n" + "="*60)
        logger.info("필터 버튼 클릭 시작 (월요일 기준)")
        logger.info("="*60)
        
        # 먼저 월요일 클릭
        try:
            weekday_button = driver.find_element(By.XPATH, "//button[contains(text(), '월')]")
            driver.execute_script("arguments[0].click();", weekday_button)
            time.sleep(wait_time)
        except:
            pass
        
        for filter_name in FILTERS:
            try:
                logger.info(f"\n[{filter_name}] 필터 클릭 시도...")
                
                # 필터 버튼 찾기 (HTML 구조: <button> 안에 <span> 태그)
                filter_button = None
                selectors = [
                    f"//button[.//span[text()='{filter_name}']]",  # <button> 안에 <span>이 있는 경우
                    f"//button[contains(., '{filter_name}')]",  # <button> 안에 텍스트가 있는 경우
                    f"//span[text()='{filter_name}']/ancestor::button[1]",  # <span>의 부모 <button>
                ]
                
                for selector in selectors:
                    try:
                        filter_button = driver.find_element(By.XPATH, selector)
                        if filter_button:
                            break
                    except:
                        continue
                
                if not filter_button:
                    logger.warning(f"[{filter_name}] 필터 버튼을 찾을 수 없습니다.")
                    continue
                
                # 클릭 전 네트워크 로그 초기화
                driver.get_log('performance')
                
                # 버튼 클릭
                driver.execute_script("arguments[0].click();", filter_button)
                logger.info(f"[{filter_name}] 필터 버튼 클릭 완료")
                
                # 클릭 후 대기
                time.sleep(wait_time)
                
                # 네트워크 요청 수집
                apis = collect_network_requests(driver, action=f"필터_{filter_name}")
                all_api_endpoints.extend(apis)
                logger.info(f"[{filter_name}] {len(apis)}개 API 발견")
                
            except Exception as e:
                logger.error(f"[{filter_name}] 필터 클릭 실패: {e}")
                continue
        
        # 3. 정렬 버튼 클릭
        logger.info("\n" + "="*60)
        logger.info("정렬 버튼 클릭 시작")
        logger.info("="*60)
        
        for sort_option in SORT_OPTIONS:
            try:
                logger.info(f"\n[{sort_option}] 정렬 클릭 시도...")
                
                # 정렬 버튼 찾기
                sort_button = None
                selectors = [
                    f"//button[contains(text(), '{sort_option}')]",
                    f"//a[contains(text(), '{sort_option}')]",
                    f"//div[contains(text(), '{sort_option}')]",
                    f"//span[contains(text(), '{sort_option}')]",
                ]
                
                for selector in selectors:
                    try:
                        sort_button = driver.find_element(By.XPATH, selector)
                        if sort_button:
                            break
                    except:
                        continue
                
                if not sort_button:
                    logger.warning(f"[{sort_option}] 정렬 버튼을 찾을 수 없습니다.")
                    continue
                
                # 클릭 전 네트워크 로그 초기화
                driver.get_log('performance')
                
                # 버튼 클릭
                driver.execute_script("arguments[0].click();", sort_button)
                logger.info(f"[{sort_option}] 정렬 버튼 클릭 완료")
                
                # 클릭 후 대기
                time.sleep(wait_time)
                
                # 네트워크 요청 수집
                apis = collect_network_requests(driver, action=f"정렬_{sort_option}")
                all_api_endpoints.extend(apis)
                logger.info(f"[{sort_option}] {len(apis)}개 API 발견")
                
            except Exception as e:
                logger.error(f"[{sort_option}] 정렬 클릭 실패: {e}")
                continue
        
        # 중복 제거
        unique_apis = []
        seen_urls = set()
        for api in all_api_endpoints:
            url = api.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_apis.append(api)
        
        logger.info(f"\n총 {len(unique_apis)}개의 고유한 API 엔드포인트 발견")
        return unique_apis
        
    except Exception as e:
        logger.error(f"Selenium 실행 실패: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def collect_network_requests(driver, action: str = "") -> List[Dict[str, Any]]:
    """
    현재까지의 네트워크 요청을 수집합니다.
    
    Args:
        driver: Selenium WebDriver
        action: 수행한 동작 이름 (디버깅용)
    
    Returns:
        API 엔드포인트 리스트
    """
    api_endpoints = []
    
    try:
        logs = driver.get_log('performance')
        
        for log in logs:
            try:
                message = json.loads(log['message'])
                method = message.get('message', {}).get('method', '')
                params = message.get('message', {}).get('params', {})
                
                if method == 'Network.responseReceived':
                    response = params.get('response', {})
                    request_url = response.get('url', '')
                    status = response.get('status', 0)
                    mime_type = response.get('mimeType', '')
                    
                    # API 엔드포인트 후보 찾기
                    if any(keyword in request_url.lower() for keyword in ['api', 'webtoon', 'chart', 'list', 'rank', 'title', 'episode']):
                        # 중복 체크
                        if not any(ep['url'] == request_url for ep in api_endpoints):
                            api_endpoints.append({
                                'url': request_url,
                                'status': status,
                                'mime_type': mime_type,
                                'method': 'GET',
                                'action': action,
                                'headers': response.get('headers', {})
                            })
                
                elif method == 'Network.requestWillBeSent':
                    request = params.get('request', {})
                    request_url = request.get('url', '')
                    request_method = request.get('method', 'GET')
                    
                    if any(keyword in request_url.lower() for keyword in ['api', 'webtoon', 'chart', 'list', 'rank', 'title', 'episode']):
                        if not any(ep['url'] == request_url for ep in api_endpoints):
                            api_endpoints.append({
                                'url': request_url,
                                'status': None,
                                'mime_type': None,
                                'method': request_method,
                                'action': action,
                                'headers': request.get('headers', {}),
                                'post_data': request.get('postData')
                            })
            except:
                continue
        
        return api_endpoints
        
    except Exception as e:
        logger.error(f"네트워크 요청 수집 실패: {e}")
        return []


def save_results(api_endpoints: List[Dict[str, Any]], output_dir: Path) -> None:
    """결과 저장"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filepath = output_dir / f"api_endpoints_clicks_{timestamp}.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(api_endpoints, f, ensure_ascii=False, indent=2)
    
    logger.info(f"API 엔드포인트 저장: {filepath}")


def main():
    """메인 함수"""
    output_dir = Path(__file__).parent.parent / 'data' / 'analysis'
    
    logger.info("=" * 60)
    logger.info("카카오 웹툰 API 엔드포인트 찾기 (버튼 클릭 포함)")
    logger.info("=" * 60)
    
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 설치되어 있지 않습니다.")
        return
    
    # 버튼 클릭을 포함한 API 엔드포인트 찾기
    api_endpoints = find_api_with_clicks(KAKAO_WEBTOON_URL, wait_time=5)
    
    if not api_endpoints:
        logger.warning("API 엔드포인트를 찾을 수 없습니다.")
        return
    
    # 결과 저장
    save_results(api_endpoints, output_dir)
    
    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("발견된 API 엔드포인트 요약")
    logger.info("=" * 60)
    
    for api in api_endpoints[:20]:  # 처음 20개만
        action = api.get('action', 'unknown')
        url = api.get('url', 'N/A')
        method = api.get('method', 'GET')
        logger.info(f"[{action}] {method} {url}")
    
    logger.info(f"\n총 {len(api_endpoints)}개의 API 엔드포인트 발견")
    logger.info("분석 완료!")


if __name__ == "__main__":
    main()

