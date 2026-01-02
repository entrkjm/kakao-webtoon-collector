"""
카카오 웹툰 정렬 옵션 API 찾기

정렬 버튼 클릭 시 어떤 API가 호출되는지 확인합니다.
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
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.error("Selenium이 설치되어 있지 않습니다.")

KAKAO_WEBTOON_URL = "https://webtoon.kakao.com"

# 정렬 옵션 (예상)
SORT_OPTIONS = ['최신순', '조회순', '전체인기순', '남자인기순', '여자인기순']


def find_sort_api() -> List[Dict[str, Any]]:
    """정렬 버튼 클릭 시 호출되는 API 찾기"""
    
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 필요합니다.")
        return []
    
    api_calls = []
    
    # Chrome 옵션 설정
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
            window._apiCalls.push({
                type: 'fetch',
                url: args[0],
                method: args[1]?.method || 'GET',
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
        time.sleep(3)
        
        # 월요일 버튼 클릭 (요일 선택)
        try:
            mon_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//li[./p[text()='월']]"))
            )
            driver.execute_script("arguments[0].click();", mon_button)
            logger.info("월요일 버튼 클릭")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"월요일 버튼 클릭 실패: {e}")
        
        # 정렬 버튼 찾기 및 클릭
        for sort_option in SORT_OPTIONS:
            try:
                # 정렬 버튼 찾기 (다양한 선택자 시도)
                sort_button = None
                selectors = [
                    f"//button[.//span[text()='{sort_option}']]",
                    f"//span[text()='{sort_option}']/ancestor::button[1]",
                    f"//button[contains(text(), '{sort_option}')]",
                    f"//div[contains(text(), '{sort_option}')]/ancestor::button[1]",
                ]
                
                for selector in selectors:
                    try:
                        sort_button = driver.find_element(By.XPATH, selector)
                        if sort_button:
                            break
                    except:
                        continue
                
                if not sort_button:
                    logger.warning(f"정렬 버튼을 찾을 수 없습니다: {sort_option}")
                    continue
                
                # 로그 초기화
                driver.execute_script("window._apiCalls = [];")
                
                # 정렬 버튼 클릭
                driver.execute_script("arguments[0].click();", sort_button)
                logger.info(f"정렬 버튼 클릭: {sort_option}")
                
                # API 호출 대기
                time.sleep(3)
                
                # API 호출 확인
                calls = driver.execute_script("return window._apiCalls || [];")
                
                # gateway-kw.kakao.com 관련 API만 필터링
                relevant_calls = [
                    call for call in calls
                    if 'gateway-kw.kakao.com' in call.get('url', '')
                ]
                
                if relevant_calls:
                    logger.info(f"✓ {sort_option}: {len(relevant_calls)}개 API 호출 발견")
                    for call in relevant_calls:
                        logger.info(f"  - {call['url']}")
                        api_calls.append({
                            'sort_option': sort_option,
                            'api_call': call
                        })
                else:
                    logger.warning(f"✗ {sort_option}: 관련 API 호출 없음")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"정렬 옵션 '{sort_option}' 처리 중 오류: {e}")
                continue
        
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
    logger.info("카카오 웹툰 정렬 옵션 API 찾기")
    logger.info("=" * 60)
    
    api_calls = find_sort_api()
    
    # 결과 저장
    output_dir = Path("data/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"sort_api_search_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(api_calls, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n결과 저장: {output_file}")
    
    # 요약 출력
    logger.info("\n" + "=" * 60)
    logger.info("결과 요약")
    logger.info("=" * 60)
    
    if api_calls:
        logger.info(f"총 {len(api_calls)}개 API 호출 발견")
        
        # 정렬 옵션별로 그룹화
        by_sort = {}
        for item in api_calls:
            sort_option = item['sort_option']
            if sort_option not in by_sort:
                by_sort[sort_option] = []
            by_sort[sort_option].append(item['api_call']['url'])
        
        for sort_option, urls in by_sort.items():
            logger.info(f"\n{sort_option}:")
            for url in set(urls):  # 중복 제거
                logger.info(f"  - {url}")
    else:
        logger.warning("API 호출을 찾을 수 없습니다.")


if __name__ == "__main__":
    main()

