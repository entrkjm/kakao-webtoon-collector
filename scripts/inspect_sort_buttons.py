"""
카카오 웹툰 정렬 버튼 구조 확인
"""

import logging
import time
from pathlib import Path

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


def inspect_sort_buttons():
    """정렬 버튼 구조 확인"""
    
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 필요합니다.")
        return
    
    chrome_options = Options()
    # headless 모드 해제 (디버깅용)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(KAKAO_WEBTOON_URL)
        
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
        
        # 정렬 관련 요소 찾기
        logger.info("\n=== 정렬 관련 요소 찾기 ===")
        
        # 버튼 요소 찾기
        buttons = driver.find_elements(By.TAG_NAME, "button")
        logger.info(f"총 {len(buttons)}개 버튼 발견")
        
        sort_keywords = ['정렬', '순', '인기', '조회', '최신', '남자', '여자', '전체']
        
        for i, button in enumerate(buttons[:50]):  # 처음 50개만 확인
            try:
                text = button.text.strip()
                if text and any(keyword in text for keyword in sort_keywords):
                    logger.info(f"\n버튼 {i}: {text}")
                    logger.info(f"  - XPath: {driver.execute_script('return arguments[0].getAttribute(\"xpath\") || \"N/A\"', button)}")
                    logger.info(f"  - 클래스: {button.get_attribute('class')}")
                    logger.info(f"  - ID: {button.get_attribute('id')}")
            except:
                pass
        
        # 드롭다운이나 셀렉트 요소 찾기
        selects = driver.find_elements(By.TAG_NAME, "select")
        logger.info(f"\n총 {len(selects)}개 select 요소 발견")
        
        for i, select in enumerate(selects):
            try:
                logger.info(f"\nSelect {i}:")
                logger.info(f"  - ID: {select.get_attribute('id')}")
                logger.info(f"  - 클래스: {select.get_attribute('class')}")
                options = select.find_elements(By.TAG_NAME, "option")
                for opt in options:
                    logger.info(f"    - 옵션: {opt.text}")
            except:
                pass
        
        # 페이지 소스 일부 저장
        output_dir = Path("data/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        page_source = driver.page_source
        output_file = output_dir / "page_source_sort_inspection.html"
        output_file.write_text(page_source, encoding='utf-8')
        logger.info(f"\n페이지 소스 저장: {output_file}")
        
        # 10초 대기 (수동 확인용)
        logger.info("\n10초 대기 중... (브라우저에서 수동 확인 가능)")
        time.sleep(10)
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            input("Enter 키를 누르면 브라우저를 닫습니다...")
            driver.quit()


if __name__ == "__main__":
    inspect_sort_buttons()

