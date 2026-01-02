"""
카카오 웹툰 정렬 API 상세 검색

실제 브라우저에서 정렬 버튼을 클릭하여 API 호출을 확인합니다.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

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


def find_sort_api_detailed() -> List[Dict[str, Any]]:
    """정렬 버튼 클릭 시 호출되는 API 상세 검색"""
    
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 필요합니다.")
        return []
    
    api_calls = []
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 인터셉터 스크립트
    interceptor_script = """
    (function() {
        const originalFetch = window.fetch;
        const originalXHR = window.XMLHttpRequest.prototype.open;
        
        window._apiCalls = [];
        
        window.fetch = function(...args) {
            const url = args[0];
            window._apiCalls.push({
                type: 'fetch',
                url: url,
                method: args[1]?.method || 'GET',
                params: args[1]?.body || null,
                timestamp: new Date().toISOString()
            });
            return originalFetch.apply(this, args);
        };
        
        XMLHttpRequest.prototype.open = function(method, url, ...args) {
            window._apiCalls.push({
                type: 'xhr',
                url: url,
                method: method,
                timestamp: new Date().toISOString()
            });
            return originalXHR.apply(this, [method, url, ...args]);
        };
    })();
    """
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(KAKAO_WEBTOON_URL)
        
        # 인터셉터 설치
        driver.execute_script(interceptor_script)
        logger.info("인터셉터 설치 완료")
        
        # 페이지 로드 대기
        time.sleep(5)
        
        # 월요일 버튼 클릭
        try:
            mon_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//li[./p[text()='월']]"))
            )
            driver.execute_script("arguments[0].click();", mon_button)
            logger.info("월요일 버튼 클릭")
            time.sleep(3)
        except Exception as e:
            logger.warning(f"월요일 버튼 클릭 실패: {e}")
        
        # 기본 API 호출 확인
        initial_calls = driver.execute_script("return window._apiCalls || [];")
        gateway_calls = [c for c in initial_calls if 'gateway-kw.kakao.com' in c.get('url', '')]
        if gateway_calls:
            logger.info(f"초기 API 호출: {len(gateway_calls)}개")
            for call in gateway_calls:
                logger.info(f"  - {call['url']}")
                api_calls.append({
                    'step': 'initial',
                    'api_call': call
                })
        
        # 정렬 관련 모든 요소 찾기
        logger.info("\n=== 정렬 관련 요소 찾기 ===")
        
        # 모든 클릭 가능한 요소 찾기
        clickable_elements = driver.find_elements(By.XPATH, "//*[@onclick or @role='button' or self::button or self::a]")
        logger.info(f"총 {len(clickable_elements)}개 클릭 가능한 요소 발견")
        
        sort_keywords = ['정렬', '순', '인기', '조회', '최신', '남자', '여자', '전체', 'popularity', 'views', 'createdAt']
        
        for i, elem in enumerate(clickable_elements[:100]):  # 처음 100개만 확인
            try:
                text = elem.text.strip()
                tag = elem.tag_name
                classes = elem.get_attribute('class') or ''
                
                if text and any(keyword in text for keyword in sort_keywords):
                    logger.info(f"\n요소 {i}: {tag} - {text[:50]}")
                    logger.info(f"  - 클래스: {classes[:100]}")
                    
                    # 로그 초기화
                    driver.execute_script("window._apiCalls = [];")
                    
                    # 클릭 시도
                    try:
                        driver.execute_script("arguments[0].click();", elem)
                        time.sleep(2)
                        
                        # API 호출 확인
                        calls = driver.execute_script("return window._apiCalls || [];")
                        gateway_calls = [c for c in calls if 'gateway-kw.kakao.com' in c.get('url', '')]
                        
                        if gateway_calls:
                            logger.info(f"  ✓ API 호출 발견: {len(gateway_calls)}개")
                            for call in gateway_calls:
                                logger.info(f"    - {call['url']}")
                                api_calls.append({
                                    'step': f'click_{i}',
                                    'element_text': text[:50],
                                    'api_call': call
                                })
                    except Exception as e:
                        logger.debug(f"  클릭 실패: {e}")
                        
            except Exception as e:
                continue
        
        # 페이지 소스 저장
        output_dir = Path("data/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        page_source = driver.page_source
        output_file = output_dir / "page_source_sort_detailed.html"
        output_file.write_text(page_source, encoding='utf-8')
        logger.info(f"\n페이지 소스 저장: {output_file}")
        
        return api_calls
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if driver:
            driver.quit()


def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("카카오 웹툰 정렬 API 상세 검색")
    logger.info("=" * 60)
    
    api_calls = find_sort_api_detailed()
    
    # 결과 저장
    output_dir = Path("data/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"sort_api_detailed_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(api_calls, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n결과 저장: {output_file}")
    
    # 요약
    logger.info("\n" + "=" * 60)
    logger.info("결과 요약")
    logger.info("=" * 60)
    logger.info(f"총 {len(api_calls)}개 API 호출 발견")


if __name__ == "__main__":
    main()

