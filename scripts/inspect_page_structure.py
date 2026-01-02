"""
카카오 웹툰 페이지 구조 상세 분석

실제 HTML 구조를 확인하여 버튼 선택자를 정확히 찾습니다.
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
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

KAKAO_WEBTOON_URL = "https://webtoon.kakao.com"


def inspect_page_structure():
    """페이지 구조를 상세히 분석합니다."""
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 설치되어 있지 않습니다.")
        return
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("페이지 로딩 중...")
        driver.get(KAKAO_WEBTOON_URL)
        time.sleep(5)
        
        # 페이지 소스 저장
        html = driver.page_source
        output_dir = Path(__file__).parent.parent / 'data' / 'analysis'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        html_file = output_dir / 'page_source_full.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"전체 HTML 저장: {html_file}")
        
        # 버튼 요소 찾기
        logger.info("\n" + "="*60)
        logger.info("요일 버튼 찾기")
        logger.info("="*60)
        
        for weekday in ['월', '화', '수', '목', '금', '토', '일']:
            try:
                # 다양한 선택자 시도
                selectors = [
                    f"//button[contains(text(), '{weekday}')]",
                    f"//a[contains(text(), '{weekday}')]",
                    f"//div[contains(text(), '{weekday}')]",
                    f"//span[contains(text(), '{weekday}')]",
                    f"//*[contains(text(), '{weekday}')]",
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            logger.info(f"[{weekday}] 발견: {selector}")
                            for elem in elements[:3]:  # 처음 3개만
                                try:
                                    tag = elem.tag_name
                                    classes = elem.get_attribute('class')
                                    text = elem.text
                                    logger.info(f"  - 태그: {tag}, 클래스: {classes}, 텍스트: {text[:50]}")
                                except:
                                    pass
                            break
                    except:
                        continue
            except Exception as e:
                logger.error(f"[{weekday}] 오류: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("필터 버튼 찾기")
        logger.info("="*60)
        
        for filter_name in ['전체', '연재무료', '기다무']:
            try:
                selectors = [
                    f"//button[contains(text(), '{filter_name}')]",
                    f"//a[contains(text(), '{filter_name}')]",
                    f"//div[contains(text(), '{filter_name}')]",
                    f"//span[contains(text(), '{filter_name}')]",
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            logger.info(f"[{filter_name}] 발견: {selector}")
                            for elem in elements[:3]:
                                try:
                                    tag = elem.tag_name
                                    classes = elem.get_attribute('class')
                                    text = elem.text
                                    logger.info(f"  - 태그: {tag}, 클래스: {classes}, 텍스트: {text[:50]}")
                                except:
                                    pass
                            break
                    except:
                        continue
            except Exception as e:
                logger.error(f"[{filter_name}] 오류: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("정렬 버튼 찾기")
        logger.info("="*60)
        
        for sort_option in ['최신순', '조회순', '전체인기순', '남자인기순', '여자인기순']:
            try:
                selectors = [
                    f"//button[contains(text(), '{sort_option}')]",
                    f"//a[contains(text(), '{sort_option}')]",
                    f"//div[contains(text(), '{sort_option}')]",
                    f"//span[contains(text(), '{sort_option}')]",
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            logger.info(f"[{sort_option}] 발견: {selector}")
                            for elem in elements[:3]:
                                try:
                                    tag = elem.tag_name
                                    classes = elem.get_attribute('class')
                                    text = elem.text
                                    logger.info(f"  - 태그: {tag}, 클래스: {classes}, 텍스트: {text[:50]}")
                                except:
                                    pass
                            break
                    except:
                        continue
            except Exception as e:
                logger.error(f"[{sort_option}] 오류: {e}")
        
        # 모든 버튼 요소 찾기
        logger.info("\n" + "="*60)
        logger.info("모든 버튼 요소 찾기")
        logger.info("="*60)
        
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        logger.info(f"총 {len(buttons)}개의 button 태그 발견")
        for i, btn in enumerate(buttons[:20]):  # 처음 20개만
            try:
                text = btn.text.strip()
                classes = btn.get_attribute('class')
                if text:
                    logger.info(f"  [{i+1}] 텍스트: '{text[:30]}', 클래스: {classes}")
            except:
                pass
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    inspect_page_structure()

