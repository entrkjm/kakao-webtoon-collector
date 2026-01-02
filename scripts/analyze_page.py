"""
카카오 웹툰 페이지 구조 분석 스크립트

이 스크립트는 실제 카카오 웹툰 페이지를 방문하여:
1. HTML 구조를 분석
2. API 엔드포인트 확인
3. JavaScript 네트워크 요청 모니터링
4. 데이터 구조 파악

실행 방법:
    python scripts/analyze_page.py
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

# Selenium은 선택적 (설치되어 있으면 사용)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 카카오 웹툰 URL
KAKAO_WEBTOON_URL = "https://webtoon.kakao.com"
KAKAO_WEBTOON_MOBILE_URL = "https://m.webtoon.kakao.com"


def analyze_with_requests(url: str) -> Dict[str, Any]:
    """
    requests를 사용하여 페이지를 분석합니다.
    
    Args:
        url: 분석할 URL
    
    Returns:
        분석 결과 딕셔너리
    """
    logger.info(f"requests로 페이지 분석 시작: {url}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
    })
    
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'lxml')
        
        result = {
            'method': 'requests',
            'url': url,
            'status_code': response.status_code,
            'html_length': len(html),
            'title': soup.title.string if soup.title else None,
            'scripts': [],
            'api_endpoints': [],
            'webtoon_links': [],
            'sample_html': html[:5000] if len(html) > 5000 else html
        }
        
        # 스크립트 태그에서 API 엔드포인트 찾기
        for script in soup.find_all('script'):
            script_src = script.get('src', '')
            script_content = script.string or ''
            
            if script_src:
                result['scripts'].append({
                    'type': 'external',
                    'src': script_src
                })
            
            # API 엔드포인트 패턴 찾기
            api_patterns = [
                r'["\']([^"\']*api[^"\']*)["\']',
                r'["\']([^"\']*webtoon[^"\']*)["\']',
                r'url:\s*["\']([^"\']*)["\']',
                r'endpoint:\s*["\']([^"\']*)["\']',
            ]
            
            for pattern in api_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                for match in matches:
                    if 'api' in match.lower() or 'webtoon' in match.lower():
                        if match not in result['api_endpoints']:
                            result['api_endpoints'].append(match)
        
        # 웹툰 링크 찾기
        link_patterns = [
            'a[href*="webtoon"]',
            'a[href*="viewer"]',
            'a[href*="/viewer/"]',
        ]
        
        for pattern in link_patterns:
            links = soup.select(pattern)
            for link in links[:10]:  # 처음 10개만
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if href and text:
                    result['webtoon_links'].append({
                        'href': href,
                        'text': text[:50]  # 처음 50자만
                    })
        
        return result
        
    except Exception as e:
        logger.error(f"requests 분석 실패: {e}")
        return {'method': 'requests', 'url': url, 'error': str(e)}


def analyze_with_selenium(url: str, headless: bool = True) -> Dict[str, Any]:
    """
    Selenium을 사용하여 JavaScript가 실행된 페이지를 분석합니다.
    
    Args:
        url: 분석할 URL
        headless: 헤드리스 모드 사용 여부
    
    Returns:
        분석 결과 딕셔너리
    """
    if not SELENIUM_AVAILABLE:
        return {'method': 'selenium', 'url': url, 'error': 'Selenium이 설치되어 있지 않습니다.'}
    
    logger.info(f"Selenium으로 페이지 분석 시작: {url}")
    
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
    
    # 네트워크 로그 활성화
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        # 추가 대기 (동적 콘텐츠 로딩)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # 네트워크 로그 수집
        logs = driver.get_log('performance')
        network_requests = []
        api_requests = []
        
        for log in logs:
            try:
                message = json.loads(log['message'])
                method = message.get('message', {}).get('method', '')
                params = message.get('message', {}).get('params', {})
                
                if method == 'Network.responseReceived':
                    response = params.get('response', {})
                    url = response.get('url', '')
                    status = response.get('status', 0)
                    
                    network_requests.append({
                        'url': url,
                        'status': status,
                        'type': response.get('mimeType', '')
                    })
                    
                    # API 엔드포인트 찾기
                    if 'api' in url.lower() or 'webtoon' in url.lower():
                        api_requests.append({
                            'url': url,
                            'status': status,
                            'type': response.get('mimeType', '')
                        })
            except:
                continue
        
        # 페이지 소스 가져오기
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # 웹툰 링크 찾기
        webtoon_links = []
        link_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="webtoon"], a[href*="viewer"]')
        for link in link_elements[:20]:  # 처음 20개만
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                if href and text:
                    webtoon_links.append({
                        'href': href,
                        'text': text[:50]
                    })
            except:
                continue
        
        result = {
            'method': 'selenium',
            'url': url,
            'html_length': len(html),
            'title': driver.title,
            'current_url': driver.current_url,
            'network_requests_count': len(network_requests),
            'api_requests': api_requests[:20],  # 처음 20개만
            'webtoon_links': webtoon_links,
            'sample_html': html[:5000] if len(html) > 5000 else html
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Selenium 분석 실패: {e}")
        return {'method': 'selenium', 'url': url, 'error': str(e)}
    finally:
        if driver:
            driver.quit()


def save_analysis_result(result: Dict[str, Any], output_dir: Path) -> None:
    """
    분석 결과를 파일로 저장합니다.
    
    Args:
        result: 분석 결과
        output_dir: 출력 디렉토리
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    method = result.get('method', 'unknown')
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f"analysis_{method}_{timestamp}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"분석 결과 저장: {filepath}")
    
    # HTML 샘플도 별도로 저장
    if 'sample_html' in result:
        html_filepath = output_dir / f"sample_{method}_{timestamp}.html"
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(result['sample_html'])
        logger.info(f"HTML 샘플 저장: {html_filepath}")


def main():
    """메인 함수"""
    output_dir = Path(__file__).parent.parent / 'data' / 'analysis'
    
    logger.info("=" * 60)
    logger.info("카카오 웹툰 페이지 구조 분석 시작")
    logger.info("=" * 60)
    
    # 1. requests로 분석
    logger.info("\n[1단계] requests로 페이지 분석")
    result_requests = analyze_with_requests(KAKAO_WEBTOON_URL)
    save_analysis_result(result_requests, output_dir)
    
    # 2. Selenium으로 분석 (JavaScript 실행)
    logger.info("\n[2단계] Selenium으로 페이지 분석 (JavaScript 실행)")
    try:
        result_selenium = analyze_with_selenium(KAKAO_WEBTOON_URL, headless=True)
        save_analysis_result(result_selenium, output_dir)
    except Exception as e:
        logger.error(f"Selenium 분석 실패 (ChromeDriver 필요): {e}")
        logger.info("ChromeDriver가 설치되어 있지 않으면 Selenium 분석을 건너뜁니다.")
    
    # 3. 모바일 버전 분석
    logger.info("\n[3단계] 모바일 버전 페이지 분석")
    result_mobile = analyze_with_requests(KAKAO_WEBTOON_MOBILE_URL)
    save_analysis_result(result_mobile, output_dir)
    
    # 결과 요약 출력
    logger.info("\n" + "=" * 60)
    logger.info("분석 결과 요약")
    logger.info("=" * 60)
    
    if 'api_endpoints' in result_requests:
        logger.info(f"\n발견된 API 엔드포인트 (requests): {len(result_requests['api_endpoints'])}개")
        for endpoint in result_requests['api_endpoints'][:10]:
            logger.info(f"  - {endpoint}")
    
    if 'api_requests' in result_selenium:
        logger.info(f"\n발견된 API 요청 (Selenium): {len(result_selenium.get('api_requests', []))}개")
        for req in result_selenium.get('api_requests', [])[:10]:
            logger.info(f"  - {req.get('url', 'N/A')} (Status: {req.get('status', 'N/A')})")
    
    if 'webtoon_links' in result_requests:
        logger.info(f"\n발견된 웹툰 링크 (requests): {len(result_requests['webtoon_links'])}개")
        for link in result_requests['webtoon_links'][:5]:
            logger.info(f"  - {link.get('text', 'N/A')}: {link.get('href', 'N/A')}")
    
    logger.info("\n분석 완료! 결과는 data/analysis/ 디렉토리에 저장되었습니다.")


if __name__ == "__main__":
    main()

