"""
정렬 옵션별 데이터 수집 모듈

Selenium을 사용하여 실제 브라우저에서 정렬 버튼을 클릭하고
각 정렬 옵션별 데이터를 수집합니다.
"""

import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any, List

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
    logger.warning("Selenium이 설치되어 있지 않습니다. 클라이언트 사이드 정렬 수집을 사용할 수 없습니다.")

from src.extract import SORT_OPTIONS, WEEKDAY_MAPPING
from src.utils import get_raw_html_dir

KAKAO_WEBTOON_URL = "https://webtoon.kakao.com"


def sort_cards_by_key(api_data: Dict[str, Any], sort_key: str) -> List[Dict[str, Any]]:
    """
    API 데이터에서 카드를 추출하고 정렬 키에 따라 정렬합니다.
    
    Args:
        api_data: API 응답 데이터
        sort_key: 정렬 키 ('popularity', 'views', 'createdAt', 'popularityMale', 'popularityFemale')
    
    Returns:
        정렬된 카드 리스트
    """
    try:
        all_cards = []
        
        # data 배열에서 모든 카드 추출
        data_list = api_data.get('data', [])
        for data_item in data_list:
            if not isinstance(data_item, dict):
                continue
            
            card_groups = data_item.get('cardGroups', [])
            for card_group in card_groups:
                if not isinstance(card_group, dict):
                    continue
                
                cards = card_group.get('cards', [])
                for card in cards:
                    if isinstance(card, dict):
                        all_cards.append(card)
        
        if not all_cards:
            return []
        
        # 정렬 키에 따라 정렬
        # sorting 객체에서 정렬 값 가져오기
        def get_sort_value(card):
            sorting = card.get('sorting', {})
            if isinstance(sorting, dict):
                return sorting.get(sort_key, 0)
            return 0
        
        # 내림차순 정렬 (높은 값이 먼저)
        sorted_cards = sorted(all_cards, key=get_sort_value, reverse=True)
        
        logger.info(f"총 {len(sorted_cards)}개 카드를 {sort_key} 기준으로 정렬")
        
        return sorted_cards
        
    except Exception as e:
        logger.error(f"카드 정렬 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def extract_data_from_dom(driver: webdriver.Chrome, sort_key: str, sort_name: str) -> Optional[Dict[str, Any]]:
    """
    DOM에서 직접 웹툰 데이터를 추출합니다.
    정렬이 클라이언트 사이드에서 처리되는 경우 사용합니다.
    """
    try:
        # 페이지 소스에서 __NEXT_DATA__ 추출 시도
        page_source = driver.page_source
        
        # __NEXT_DATA__ 스크립트 태그 찾기
        import re
        next_data_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_source, re.DOTALL)
        if next_data_match:
            try:
                next_data = json.loads(next_data_match.group(1))
                logger.info("__NEXT_DATA__에서 데이터 추출 시도")
                
                # __NEXT_DATA__ 구조에서 웹툰 데이터 추출
                # props.pageProps.dehydratedState.queries에서 데이터 찾기
                props = next_data.get('props', {})
                page_props = props.get('pageProps', {})
                initial_props = page_props.get('initialProps', {})
                dehydrated_state = initial_props.get('dehydratedState', {})
                queries = dehydrated_state.get('queries', [])
                
                for query in queries:
                    state = query.get('state', {})
                    data = state.get('data', {})
                    
                    # API 응답 데이터 찾기
                    if isinstance(data, dict) and 'success' in data and data.get('success'):
                        result_data = data.get('data', {})
                        if isinstance(result_data, dict) and 'data' in result_data:
                            # 정렬 정보가 포함된 데이터
                            api_data = result_data
                            
                            # 정렬 키에 따라 정렬
                            sorted_cards = sort_cards_by_key(api_data, sort_key)
                            
                            if sorted_cards:
                                # 정렬된 데이터로 재구성
                                sorted_data = {
                                    'data': [{
                                        'cardGroups': [{
                                            'cards': sorted_cards
                                        }]
                                    }],
                                    '_sort_key': sort_key,
                                    '_sort_name': sort_name,
                                    '_weekday': 'mon',
                                    '_source': 'next_data_sorted'
                                }
                                
                                logger.info(f"__NEXT_DATA__에서 {len(sorted_cards)}개 웹툰 추출 및 정렬 완료 ({sort_name})")
                                return sorted_data
            except Exception as e:
                logger.warning(f"__NEXT_DATA__ 파싱 실패: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        
        # JavaScript로 DOM에서 직접 데이터 추출
        extract_script = """
        (function() {
            const webtoons = [];
            
            // 다양한 선택자로 웹툰 카드 찾기
            const selectors = [
                'a[href*="/viewer/"]',
                '[data-testid*="webtoon"]',
                '[class*="webtoon"]',
                '[class*="card"]',
            ];
            
            let elements = [];
            for (const selector of selectors) {
                elements = Array.from(document.querySelectorAll(selector));
                if (elements.length > 10) {
                    break;
                }
            }
            
            if (elements.length === 0) {
                return [];
            }
            
            elements.forEach((elem, index) => {
                try {
                    const link = elem.tagName === 'A' ? elem : elem.closest('a') || elem.querySelector('a');
                    if (link) {
                        const href = link.getAttribute('href') || '';
                        const titleElem = elem.querySelector('[class*="title"], [class*="Title"]') || 
                                        link.querySelector('[class*="title"], [class*="Title"]') ||
                                        elem;
                        const title = titleElem.textContent?.trim() || link.textContent?.trim() || '';
                        
                        if (title && href) {
                            // 웹툰 ID 추출 (다양한 패턴 시도)
                            let webtoonId = null;
                            const idPatterns = [
                                /\\/(\\d+)(?:\\/|$)/,
                                /viewer\\/(\\d+)/,
                                /webtoon\\/(\\d+)/,
                            ];
                            
                            for (const pattern of idPatterns) {
                                const match = href.match(pattern);
                                if (match) {
                                    webtoonId = match[1];
                                    break;
                                }
                            }
                            
                            // 작가 정보 추출 시도
                            const authorElem = elem.querySelector('[class*="author"], [class*="Author"], [class*="writer"]');
                            const author = authorElem ? authorElem.textContent?.trim() : null;
                            
                            if (webtoonId || title) {
                                webtoons.push({
                                    id: webtoonId || `dom_${index}`,
                                    title: title,
                                    href: href,
                                    author: author,
                                    rank: index + 1
                                });
                            }
                        }
                    }
                } catch (e) {
                    // 개별 요소 처리 실패는 무시
                }
            });
            
            return webtoons;
        })();
        """
        
        webtoons = driver.execute_script(extract_script)
        
        if webtoons and len(webtoons) > 0:
            logger.info(f"DOM에서 {len(webtoons)}개 웹툰 추출")
            
            # API 응답 형식으로 변환
            cards = []
            for wt in webtoons:
                content = {
                    'title': wt.get('title'),
                    'authors': []
                }
                
                if wt.get('author'):
                    content['authors'] = [{
                        'name': wt.get('author'),
                        'type': 'AUTHOR'
                    }]
                
                cards.append({
                    'id': wt.get('id'),
                    'content': content
                })
            
            # API 응답 형식으로 구성
            data = {
                'data': [{
                    'cardGroups': [{
                        'cards': cards
                    }]
                }],
                '_sort_key': sort_key,
                '_sort_name': sort_name,
                '_weekday': 'mon',
                '_source': 'dom'
            }
            
            return data
        
        return None
        
    except Exception as e:
        logger.error(f"DOM 데이터 추출 실패: {e}")
        return None


def create_selenium_driver(headless: bool = True) -> Optional[webdriver.Chrome]:
    """Selenium WebDriver 생성"""
    if not SELENIUM_AVAILABLE:
        return None
    
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Selenium WebDriver 생성 실패: {e}")
        return None


def find_sort_button(driver: webdriver.Chrome, sort_name: str) -> Optional[Any]:
    """정렬 버튼 찾기"""
    try:
        # 다양한 선택자 시도
        selectors = [
            f"//button[contains(text(), '{sort_name}')]",
            f"//span[contains(text(), '{sort_name}')]/ancestor::button[1]",
            f"//div[contains(text(), '{sort_name}')]/ancestor::button[1]",
            f"//*[@role='button' and contains(text(), '{sort_name}')]",
            f"//button[.//span[contains(text(), '{sort_name}')]]",
            f"//button[.//div[contains(text(), '{sort_name}')]]",
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
            except:
                continue
        
        # 드롭다운 메뉴에서 찾기
        try:
            # 정렬 드롭다운 열기
            dropdown = driver.find_element(By.XPATH, "//button[contains(@class, 'sort') or contains(@class, 'order')]")
            driver.execute_script("arguments[0].click();", dropdown)
            time.sleep(0.5)
            
            # 드롭다운 메뉴에서 정렬 옵션 찾기
            menu_item = driver.find_element(By.XPATH, f"//*[contains(text(), '{sort_name}')]")
            return menu_item
        except:
            pass
        
        return None
    except Exception as e:
        logger.debug(f"정렬 버튼 찾기 실패 ({sort_name}): {e}")
        return None


def extract_data_with_sort_click(
    chart_date: date,
    sort_key: str,
    collect_all_weekdays: bool = False,
    headless: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Selenium을 사용하여 정렬 버튼을 클릭하고 데이터를 수집합니다.
    
    Args:
        chart_date: 수집 날짜
        sort_key: 정렬 키 ('popularity', 'views', 'createdAt', 'popularityMale', 'popularityFemale')
        collect_all_weekdays: True이면 모든 요일 데이터 수집
        headless: True이면 headless 모드 사용
    
    Returns:
        수집된 데이터 (딕셔너리), 실패 시 None
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 필요합니다.")
        return None
    
    sort_name = SORT_OPTIONS.get(sort_key)
    if not sort_name:
        logger.error(f"알 수 없는 정렬 키: {sort_key}")
        return None
    
    driver = None
    try:
        driver = create_selenium_driver(headless=headless)
        if not driver:
            return None
        
        # 인터셉터 스크립트 설치
        interceptor_script = """
        (function() {
            const originalFetch = window.fetch;
            window._apiCalls = [];
            window._apiData = {};
            
            window.fetch = function(...args) {
                const url = args[0];
                window._apiCalls.push({
                    type: 'fetch',
                    url: url,
                    method: args[1]?.method || 'GET',
                    timestamp: new Date().toISOString()
                });
                
                const promise = originalFetch.apply(this, args);
                
                // 응답 데이터 저장
                promise.then(response => {
                    if (response.url.includes('gateway-kw.kakao.com') && response.url.includes('timetables')) {
                        return response.clone().json().then(data => {
                            window._apiData[response.url] = data;
                            return response;
                        });
                    }
                    return response;
                });
                
                return promise;
            };
        })();
        """
        
        driver.execute_script(interceptor_script)
        logger.info(f"인터셉터 설치 완료 ({sort_name})")
        
        # 페이지 로드
        driver.get(KAKAO_WEBTOON_URL)
        time.sleep(5)
        
        # 요일 선택 (모든 요일 수집 모드인 경우)
        if collect_all_weekdays:
            # 모든 요일 데이터를 수집하기 위해 각 요일을 클릭
            weekdays = ['월', '화', '수', '목', '금', '토', '일']
            all_data = []
            
            for weekday_kr in weekdays:
                try:
                    # 요일 버튼 클릭
                    weekday_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//li[./p[text()='{weekday_kr}']]"))
                    )
                    driver.execute_script("arguments[0].click();", weekday_button)
                    logger.info(f"{weekday_kr}요일 버튼 클릭")
                    time.sleep(2)
                    
                    # 정렬 버튼 클릭
                    sort_button = find_sort_button(driver, sort_name)
                    if sort_button:
                        driver.execute_script("arguments[0].click();", sort_button)
                        logger.info(f"정렬 버튼 클릭: {sort_name}")
                        time.sleep(3)
                    
                    # API 데이터 확인
                    api_data = driver.execute_script("return window._apiData;")
                    if api_data:
                        for url, data in api_data.items():
                            if isinstance(data, dict) and 'data' in data:
                                # 요일 정보 추가
                                for item in data.get('data', []):
                                    if isinstance(item, dict):
                                        item['_weekday'] = WEEKDAY_MAPPING.get(weekday_kr, weekday_kr.lower())
                                        item['_sort_key'] = sort_key
                                        item['_sort_name'] = sort_name
                                all_data.append(data)
                    
                    # 로그 초기화
                    driver.execute_script("window._apiData = {};")
                    
                except Exception as e:
                    logger.warning(f"{weekday_kr}요일 처리 실패: {e}")
                    continue
            
            if all_data:
                combined_data = {
                    'data': [],
                    '_collected_all_weekdays': True,
                    '_sort_key': sort_key,
                    '_sort_name': sort_name
                }
                for data in all_data:
                    if isinstance(data, dict) and 'data' in data:
                        combined_data['data'].extend(data['data'])
                
                logger.info(f"모든 요일 데이터 수집 완료 ({sort_name}): {len(combined_data['data'])}개 그룹")
                return combined_data
        else:
            # 단일 요일 (월요일)만 수집
            try:
                # 월요일 버튼 클릭
                mon_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//li[./p[text()='월']]"))
                )
                driver.execute_script("arguments[0].click();", mon_button)
                logger.info("월요일 버튼 클릭")
                time.sleep(2)
                
                # 정렬 버튼 클릭 시도
                sort_button = find_sort_button(driver, sort_name)
                if sort_button:
                    # 클릭 전 웹툰 목록 저장 (비교용)
                    before_click = driver.execute_script("""
                        return Array.from(document.querySelectorAll('a[href*="/viewer/"]')).slice(0, 5).map(a => a.textContent.trim());
                    """)
                    
                    driver.execute_script("arguments[0].click();", sort_button)
                    logger.info(f"정렬 버튼 클릭: {sort_name}")
                    
                    # DOM 업데이트 대기
                    time.sleep(5)
                    
                    # 클릭 후 웹툰 목록 확인
                    after_click = driver.execute_script("""
                        return Array.from(document.querySelectorAll('a[href*="/viewer/"]')).slice(0, 5).map(a => a.textContent.trim());
                    """)
                    
                    if before_click != after_click:
                        logger.info(f"정렬 변경 확인: {sort_name}")
                        logger.debug(f"  이전: {before_click[:3]}")
                        logger.debug(f"  이후: {after_click[:3]}")
                    else:
                        logger.warning(f"정렬 변경이 감지되지 않았습니다: {sort_name}")
                else:
                    logger.warning(f"정렬 버튼을 찾을 수 없습니다: {sort_name}. DOM에서 직접 추출 시도...")
                
                # API 데이터 확인
                api_data = driver.execute_script("return window._apiData;")
                if api_data:
                    for url, data in api_data.items():
                        if isinstance(data, dict) and 'data' in data:
                            # 메타데이터 추가
                            data['_sort_key'] = sort_key
                            data['_sort_name'] = sort_name
                            data['_weekday'] = 'mon'
                            logger.info(f"API 데이터 수집 완료 ({sort_name})")
                            return data
                
                # API 데이터가 없거나 정렬 버튼을 찾지 못한 경우 DOM에서 직접 추출 시도
                logger.info(f"DOM에서 직접 추출 시도 ({sort_name})...")
                try:
                    dom_data = extract_data_from_dom(driver, sort_key, sort_name)
                    if dom_data:
                        logger.info(f"DOM 데이터 수집 완료 ({sort_name}): {len(dom_data.get('data', [{}])[0].get('cardGroups', [{}])[0].get('cards', []))}개 웹툰")
                        return dom_data
                    else:
                        logger.warning(f"DOM에서 데이터를 추출할 수 없습니다 ({sort_name})")
                except Exception as e:
                    logger.error(f"DOM 추출 중 오류 발생 ({sort_name}): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                logger.warning(f"데이터를 찾을 수 없습니다 ({sort_name})")
                return None
                
            except Exception as e:
                logger.error(f"데이터 수집 실패 ({sort_name}): {e}")
                return None
        
        return None
        
    except Exception as e:
        logger.error(f"Selenium 데이터 수집 실패 ({sort_name}): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def extract_webtoon_chart_with_sort(
    chart_date: Optional[date] = None,
    sort_key: str = 'popularity',
    collect_all_weekdays: bool = False,
    headless: bool = True
) -> Optional[Path]:
    """
    정렬 옵션별로 데이터를 수집하여 저장합니다.
    
    Args:
        chart_date: 수집 날짜 (None이면 오늘 날짜)
        sort_key: 정렬 키
        collect_all_weekdays: True이면 모든 요일 데이터 수집
        headless: True이면 headless 모드 사용
    
    Returns:
        저장된 JSON 파일의 Path 객체 (실패 시 None)
    """
    if chart_date is None:
        chart_date = date.today()
    
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium이 필요합니다. pip install selenium으로 설치하세요.")
        return None
    
    try:
        # Selenium으로 데이터 수집
        data = extract_data_with_sort_click(
            chart_date=chart_date,
            sort_key=sort_key,
            collect_all_weekdays=collect_all_weekdays,
            headless=headless
        )
        
        if data is None:
            logger.error(f"데이터 수집 실패 ({sort_key})")
            return None
        
        # JSON 파일로 저장
        save_dir = get_raw_html_dir(chart_date)
        filename = f"webtoon_chart_{sort_key}.json"
        file_path = save_dir / filename
        
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        logger.info(f"JSON 저장 완료: {file_path}")
        
        # HTML 형식으로도 저장 (파싱용)
        html_filename = f"webtoon_chart_{sort_key}.html"
        html_path = save_dir / html_filename
        
        sort_info = f"<!-- Sort: {SORT_OPTIONS.get(sort_key, sort_key)} -->\n"
        html = f"{sort_info}<!-- API Response -->\n<script type='application/json' id='webtoon-data'>{json.dumps(data, ensure_ascii=False)}</script>"
        
        html_path.write_text(html, encoding='utf-8')
        logger.info(f"HTML 저장 완료: {html_path}")
        
        return html_path
        
    except Exception as e:
        logger.error(f"데이터 수집 및 저장 실패 ({sort_key}): {e}")
        import traceback
        traceback.print_exc()
        return None

