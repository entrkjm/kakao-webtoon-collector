"""
카카오 웹툰 API 엔드포인트 종합 탐색

다양한 방법으로 API를 찾습니다:
1. HTML에서 __NEXT_DATA__ 스크립트 태그 확인
2. 실제 네트워크 요청 모니터링 (XHR/Fetch)
3. JavaScript 번들에서 API 패턴 찾기
4. 요일/필터 변경 시 발생하는 요청 확인
"""

import json
import logging
import re
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
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.error("Selenium이 설치되어 있지 않습니다.")

KAKAO_WEBTOON_URL = "https://webtoon.kakao.com"


def find_next_data_in_html(html: str) -> Optional[Dict]:
    """HTML에서 __NEXT_DATA__ 스크립트 태그 찾기"""
    logger.info("HTML에서 __NEXT_DATA__ 스크립트 태그 찾기...")
    
    # __NEXT_DATA__ 패턴 찾기
    pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    
    if matches:
        try:
            data = json.loads(matches[0])
            logger.info("✓ __NEXT_DATA__ 발견!")
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"__NEXT_DATA__ 파싱 실패: {e}")
    
    # 다른 JSON 데이터 패턴 찾기
    pattern = r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    
    for match in matches:
        try:
            data = json.loads(match)
            if 'props' in data or 'webtoon' in str(data).lower() or 'title' in str(data).lower():
                logger.info("✓ JSON 데이터 발견!")
                return data
        except:
            continue
    
    logger.info("✗ __NEXT_DATA__ 또는 JSON 데이터를 찾을 수 없습니다.")
    return None


def monitor_network_requests_comprehensive(driver, wait_time: int = 10) -> List[Dict[str, Any]]:
    """종합적인 네트워크 요청 모니터링"""
    logger.info("네트워크 요청 모니터링 시작...")
    
    api_endpoints = []
    
    try:
        # Performance 로그 수집
        logs = driver.get_log('performance')
        
        for log in logs:
            try:
                message = json.loads(log['message'])
                method = message.get('message', {}).get('method', '')
                params = message.get('message', {}).get('params', {})
                
                # Network.responseReceived - 응답 받은 요청
                if method == 'Network.responseReceived':
                    response = params.get('response', {})
                    request_url = response.get('url', '')
                    status = response.get('status', 0)
                    mime_type = response.get('mimeType', '')
                    
                    # API 후보 필터링
                    if is_api_candidate(request_url, mime_type):
                        api_endpoints.append({
                            'url': request_url,
                            'status': status,
                            'mime_type': mime_type,
                            'method': 'GET',
                            'type': 'response',
                            'headers': response.get('headers', {})
                        })
                
                # Network.requestWillBeSent - 요청 전송
                elif method == 'Network.requestWillBeSent':
                    request = params.get('request', {})
                    request_url = request.get('url', '')
                    request_method = request.get('method', 'GET')
                    
                    if is_api_candidate(request_url, None):
                        api_endpoints.append({
                            'url': request_url,
                            'status': None,
                            'mime_type': None,
                            'method': request_method,
                            'type': 'request',
                            'headers': request.get('headers', {}),
                            'post_data': request.get('postData')
                        })
            except Exception as e:
                continue
        
        return api_endpoints
        
    except Exception as e:
        logger.error(f"네트워크 요청 모니터링 실패: {e}")
        return []


def is_api_candidate(url: str, mime_type: Optional[str]) -> bool:
    """API 후보인지 판단"""
    if not url:
        return False
    
    url_lower = url.lower()
    
    # 제외할 도메인
    exclude_domains = [
        'google', 'facebook', 'googletagmanager', 'doubleclick',
        'google-analytics', 'googleadservices', 'google.co.kr',
        'kakaopagecdn.com',  # CDN은 제외하지만...
        'googletagmanager.com', 'connect.facebook.net',
        'aem-kakao-collector.onkakao.net',  # Sentry
        'bc.ds.kakao.com',  # 카카오 분석
    ]
    
    for domain in exclude_domains:
        if domain in url_lower:
            return False
    
    # API 키워드 포함 여부
    api_keywords = [
        'api', 'webtoon', 'content', 'list', 'rank', 'title',
        'chart', 'episode', 'series', 'data', 'json'
    ]
    
    # 카카오 도메인인 경우 더 관대하게
    if 'kakao' in url_lower or 'kakaopage' in url_lower:
        if any(keyword in url_lower for keyword in api_keywords):
            return True
        # JSON 응답인 경우
        if mime_type and 'json' in mime_type:
            return True
    
    # 일반적인 API 패턴
    if any(keyword in url_lower for keyword in api_keywords):
        if mime_type and ('json' in mime_type or 'xml' in mime_type):
            return True
    
    return False


def find_api_in_javascript_bundles(driver) -> List[str]:
    """JavaScript 번들에서 API 엔드포인트 패턴 찾기"""
    logger.info("JavaScript 번들에서 API 패턴 찾기...")
    
    api_patterns = []
    
    try:
        # 페이지의 모든 스크립트 태그 찾기
        scripts = driver.find_elements(By.TAG_NAME, 'script')
        
        for script in scripts:
            try:
                src = script.get_attribute('src')
                if src and ('_next' in src or 'chunk' in src):
                    # Next.js 번들 파일
                    logger.info(f"  번들 파일 발견: {src}")
            except:
                continue
        
        # JavaScript 실행으로 window 객체 확인
        try:
            # window.__NEXT_DATA__ 확인
            next_data = driver.execute_script("return window.__NEXT_DATA__;")
            if next_data:
                logger.info("✓ window.__NEXT_DATA__ 발견!")
                api_patterns.append("window.__NEXT_DATA__")
        except:
            pass
        
        # fetch/XHR 인터셉터로 API 호출 확인
        try:
            # fetch와 XMLHttpRequest를 인터셉트하는 스크립트 실행
            interceptor_script = """
            (function() {
                const originalFetch = window.fetch;
                const originalXHR = window.XMLHttpRequest.prototype.open;
                
                window._apiCalls = [];
                
                window.fetch = function(...args) {
                    window._apiCalls.push({
                        type: 'fetch',
                        url: args[0],
                        method: args[1]?.method || 'GET'
                    });
                    return originalFetch.apply(this, args);
                };
                
                XMLHttpRequest.prototype.open = function(method, url, ...args) {
                    window._apiCalls.push({
                        type: 'xhr',
                        url: url,
                        method: method
                    });
                    return originalXHR.apply(this, [method, url, ...args]);
                };
            })();
            """
            driver.execute_script(interceptor_script)
            logger.info("✓ fetch/XHR 인터셉터 설치 완료")
        except Exception as e:
            logger.warning(f"인터셉터 설치 실패: {e}")
        
        return api_patterns
        
    except Exception as e:
        logger.error(f"JavaScript 번들 분석 실패: {e}")
        return []


def get_intercepted_api_calls(driver) -> List[Dict]:
    """인터셉터로 캡처한 API 호출 가져오기"""
    try:
        api_calls = driver.execute_script("return window._apiCalls || [];")
        return api_calls
    except:
        return []


def comprehensive_api_search():
    """종합적인 API 탐색"""
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 설치되어 있지 않습니다.")
        return
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
    
    # 네트워크 로그 활성화
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = None
    results = {
        'next_data': None,
        'network_requests': [],
        'intercepted_calls': [],
        'javascript_patterns': []
    }
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("=" * 60)
        logger.info("종합적인 API 탐색 시작")
        logger.info("=" * 60)
        
        # 1. 초기 페이지 로딩
        logger.info("\n[1단계] 초기 페이지 로딩...")
        driver.get(KAKAO_WEBTOON_URL)
        time.sleep(5)
        
        # HTML에서 __NEXT_DATA__ 찾기
        html = driver.page_source
        results['next_data'] = find_next_data_in_html(html)
        
        # JavaScript 인터셉터 설치
        find_api_in_javascript_bundles(driver)
        
        # 초기 네트워크 요청 수집
        initial_requests = monitor_network_requests_comprehensive(driver)
        results['network_requests'].extend(initial_requests)
        logger.info(f"초기 로딩에서 {len(initial_requests)}개 요청 발견")
        
        # 2. 요일 변경 테스트
        logger.info("\n[2단계] 요일 변경 테스트...")
        driver.get_log('performance')  # 로그 초기화
        
        try:
            # 월요일 클릭
            weekday_button = driver.find_element(By.XPATH, "//li[.//p[text()='월']]")
            driver.execute_script("arguments[0].click();", weekday_button)
            time.sleep(3)
            
            # 인터셉터로 캡처한 호출 확인
            intercepted = get_intercepted_api_calls(driver)
            results['intercepted_calls'].extend(intercepted)
            logger.info(f"인터셉터로 {len(intercepted)}개 호출 캡처")
            
            # 네트워크 요청 수집
            weekday_requests = monitor_network_requests_comprehensive(driver)
            results['network_requests'].extend(weekday_requests)
            logger.info(f"요일 변경 후 {len(weekday_requests)}개 요청 발견")
        except Exception as e:
            logger.error(f"요일 변경 실패: {e}")
        
        # 3. 필터 변경 테스트
        logger.info("\n[3단계] 필터 변경 테스트...")
        driver.get_log('performance')  # 로그 초기화
        
        try:
            # 전체 필터 클릭
            filter_button = driver.find_element(By.XPATH, "//button[.//span[text()='전체']]")
            driver.execute_script("arguments[0].click();", filter_button)
            time.sleep(3)
            
            # 인터셉터로 캡처한 호출 확인
            intercepted = get_intercepted_api_calls(driver)
            results['intercepted_calls'].extend(intercepted)
            logger.info(f"인터셉터로 {len(intercepted)}개 호출 캡처")
            
            # 네트워크 요청 수집
            filter_requests = monitor_network_requests_comprehensive(driver)
            results['network_requests'].extend(filter_requests)
            logger.info(f"필터 변경 후 {len(filter_requests)}개 요청 발견")
        except Exception as e:
            logger.error(f"필터 변경 실패: {e}")
        
        # 4. 최종 인터셉터 결과 확인
        logger.info("\n[4단계] 최종 인터셉터 결과 확인...")
        final_intercepted = get_intercepted_api_calls(driver)
        results['intercepted_calls'].extend(final_intercepted)
        
        # 중복 제거
        unique_requests = []
        seen_urls = set()
        for req in results['network_requests']:
            url = req.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_requests.append(req)
        results['network_requests'] = unique_requests
        
        # 중복 제거 (intercepted)
        unique_intercepted = []
        seen_intercepted = set()
        for req in results['intercepted_calls']:
            url = req.get('url', '')
            if url and url not in seen_intercepted:
                seen_intercepted.add(url)
                unique_intercepted.append(req)
        results['intercepted_calls'] = unique_intercepted
        
        return results
        
    except Exception as e:
        logger.error(f"종합 탐색 실패: {e}")
        return results
    finally:
        if driver:
            driver.quit()


def save_results(results: Dict, output_dir: Path) -> None:
    """결과 저장"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    
    # 전체 결과 저장
    filepath = output_dir / f"api_search_comprehensive_{timestamp}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"결과 저장: {filepath}")


def analyze_results(results: Dict) -> None:
    """결과 분석 및 원인 설명"""
    logger.info("\n" + "=" * 60)
    logger.info("결과 분석")
    logger.info("=" * 60)
    
    # __NEXT_DATA__ 확인
    if results.get('next_data'):
        logger.info("✓ __NEXT_DATA__ 발견: HTML에 데이터가 포함되어 있습니다.")
    else:
        logger.info("✗ __NEXT_DATA__ 없음: HTML에 초기 데이터가 포함되지 않았습니다.")
    
    # 네트워크 요청 분석
    network_requests = results.get('network_requests', [])
    logger.info(f"\n네트워크 요청: {len(network_requests)}개")
    
    api_candidates = [r for r in network_requests if is_api_candidate(r.get('url', ''), r.get('mime_type'))]
    logger.info(f"API 후보: {len(api_candidates)}개")
    
    for req in api_candidates[:10]:
        url = req.get('url', 'N/A')
        method = req.get('method', 'GET')
        mime_type = req.get('mime_type', 'N/A')
        logger.info(f"  [{method}] {url[:100]} ({mime_type})")
    
    # 인터셉터 결과 분석
    intercepted = results.get('intercepted_calls', [])
    logger.info(f"\n인터셉터로 캡처한 호출: {len(intercepted)}개")
    
    for call in intercepted[:10]:
        call_type = call.get('type', 'unknown')
        url = call.get('url', 'N/A')
        method = call.get('method', 'GET')
        logger.info(f"  [{call_type}] {method} {url[:100]}")
    
    # API를 찾지 못한 경우 원인 분석
    if len(api_candidates) == 0 and len(intercepted) == 0 and not results.get('next_data'):
        logger.warning("\n" + "=" * 60)
        logger.warning("API를 찾지 못한 가능한 원인")
        logger.warning("=" * 60)
        logger.warning("""
1. **서버 사이드 렌더링 (SSR)만 사용**
   - 모든 데이터가 서버에서 HTML로 렌더링됨
   - 클라이언트에서 별도 API 호출 없음
   - 해결: HTML 파싱으로 데이터 추출

2. **클라이언트 사이드 상태 관리**
   - React/Next.js의 클라이언트 상태로만 관리
   - 초기 로드 후 클라이언트에서 필터링/정렬
   - 해결: HTML에서 초기 데이터 추출 후 클라이언트 로직 재현

3. **인증이 필요한 API**
   - API가 인증 토큰이나 특정 헤더를 요구
   - 공개적으로 접근 불가
   - 해결: HTML 파싱 또는 브라우저 자동화 유지

4. **GraphQL 또는 다른 형태의 API**
   - REST API가 아닌 GraphQL 사용
   - 엔드포인트가 단일 URL일 수 있음
   - 해결: GraphQL 쿼리 분석 필요

5. **WebSocket 또는 Server-Sent Events**
   - 실시간 통신 사용
   - 일반적인 HTTP 요청이 아님
   - 해결: WebSocket 연결 모니터링 필요

6. **JavaScript 번들에 하드코딩**
   - API 엔드포인트가 JavaScript 번들에 직접 포함
   - 네트워크 요청 없이 클라이언트에서 처리
   - 해결: JavaScript 번들 분석 필요
        """)


def main():
    """메인 함수"""
    output_dir = Path(__file__).parent.parent / 'data' / 'analysis'
    
    logger.info("=" * 60)
    logger.info("카카오 웹툰 API 종합 탐색")
    logger.info("=" * 60)
    
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 설치되어 있지 않습니다.")
        return
    
    # 종합 탐색 실행
    results = comprehensive_api_search()
    
    if not results:
        logger.error("탐색 실패")
        return
    
    # 결과 저장
    save_results(results, output_dir)
    
    # 결과 분석
    analyze_results(results)
    
    logger.info("\n분석 완료!")


if __name__ == "__main__":
    main()

