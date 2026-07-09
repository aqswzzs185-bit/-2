import os
import time
import re
from playwright.sync_api import sync_playwright

def convert_text_to_html_with_links(text: str) -> str:
    """
    일반 텍스트 본문에서 URL 주소를 찾아 하이퍼링크 HTML 코드로 자동 변환하고,
    줄바꿈을 <br> 태그로 치환하여 리치 텍스트 입력을 위한 HTML 문서를 구성합니다.
    """
    # 1. HTML 특수문자 이스케이프
    html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 2. URL 패턴 감지 및 <a> 태그 변환
    # (예: 👉 http://... 형태나 일반 링크 주소를 매칭)
    url_pattern = r"(https?://[^\s\u3000]+)"
    
    def replace_url(match):
        url = match.group(1)
        # 네이버 스마트에디터가 인식하기 좋은 하이퍼링크 태그 구성
        return f'<a href="{url}" target="_blank" style="color: #0080ff; text-decoration: underline;">{url}</a>'
        
    html = re.sub(url_pattern, replace_url, html)
    
    # 3. 줄바꿈 치환
    html = html.replace("\n", "<br>")
    return html

def run_naver_publisher(
    naver_id: str, 
    title: str, 
    content: str, 
    tags: list, 
    category: str = "", 
    profile_dir: str = "./naver_chrome_profile", 
    status_callback=None
) -> dict:
    """
    Playwright를 사용하여 사용자의 로컬 크롬 세션을 통해 네이버 블로그에 포스팅을 입력하고 임시저장을 자동화합니다.
    비밀번호는 일절 저장하지 않으며 실패 시 브라우저를 종료하지 않고 대기합니다.
    """
    def log(message):
        if status_callback:
            status_callback(message)
        print(f"[Publisher Log] {message}")

    log("1단계: Playwright 모듈 초기화 및 로컬 세션 브라우저 기동 시작...")
    
    abs_profile_dir = os.path.abspath(profile_dir)
    os.makedirs(abs_profile_dir, exist_ok=True)
    
    p = sync_playwright().start()
    
    browser_context = None
    try:
        # 헤드 모드로 크롬 브라우저 실행하여 사용자에게 노출
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=abs_profile_dir,
            headless=False,
            viewport={"width": 1280, "height": 850},
            args=[
                "--disable-blink-features=AutomationControlled", # 자동화 차단 방지
                "--start-maximized"
            ]
        )
        
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        
        # 2단계: 에디터 진입 주소 설정
        if naver_id and naver_id.strip():
            target_url = f"https://blog.editor.naver.com/editor?deviceType=pc&blogId={naver_id.strip()}"
        else:
            log("네이버 ID가 설정되지 않아, 네이버 블로그 메인 페이지로 우선 진입합니다.")
            target_url = "https://section.blog.naver.com/"
            
        log(f"2단계: 네이버 목적지 이동 중... ({target_url})")
        page.goto(target_url)
        
        # 3단계: 로그인 검사 및 사용자 수동 로그인 대기 (아이디/패스워드 미저장 원칙)
        is_logged_in = False
        log("3단계: 네이버 로그인 세션 확인 및 대기 상태 돌입...")
        
        for wait_sec in range(120): # 최대 2분간 사용자가 로그인하는 것을 헤드 창에서 대기
            current_url = page.url
            if "nid.naver.com" in current_url:
                log(f"🔑 네이버 로그인이 감지되지 않았습니다. 화면의 브라우저에서 직접 로그인을 진행해 주세요. (대기 중... {wait_sec}/120초)")
                time.sleep(2)
            elif "editor.naver.com" in current_url:
                # 에디터 내부의 필수 요소 로딩 대기
                try:
                    page.wait_for_selector("textarea.se-textarea, .se-document-title", timeout=3000)
                    is_logged_in = True
                    log("에디터 페이지 내부 핵심 컴포넌트가 로딩되었습니다.")
                    break
                except:
                    log("에디터 로딩을 기다리고 있습니다...")
                    time.sleep(1)
            else:
                # 블로그 홈에 머물러 있으면 에디터 주소로 재이동
                if naver_id and naver_id.strip() and "section.blog.naver.com" in current_url:
                    log("로그인 완료 감지. 스마트에디터로 이동합니다.")
                    page.goto(f"https://blog.editor.naver.com/editor?deviceType=pc&blogId={naver_id.strip()}")
                time.sleep(2)
                
        if not is_logged_in:
            log("❌ 에러: 로그인 제한 시간을 초과했거나 에디터 페이지 진입에 실패했습니다.")
            # 오류 시에는 브라우저를 즉시 끄지 않고 사용자가 살펴볼 수 있게 유지하되 예외 처리
            return {
                "success": False, 
                "message": "로그인 제한 시간을 초과했습니다. 열린 브라우저 창에서 수동으로 마무리해 주세요.",
                "manual_mode": True,
                "playwright_instance": p,
                "context_instance": browser_context
            }
            
        log("4단계: 네이버 스마트에디터 ONE 접속 확인. 안내 레이아웃 팝업 닫기 시도...")
        time.sleep(2)
        
        # ESC 키를 사용하여 도움말 팝업 소거
        page.keyboard.press("Escape")
        time.sleep(1)
        
        # 불러오기 취소 버튼 클릭 처리
        try:
            cancel_btn = page.query_selector(".se-popup-button-cancel, button.se-btn-close")
            if cancel_btn and cancel_btn.is_visible():
                log("기존 임시 글 불러오기 알림 창 감지 ➡️ '취소' 클릭")
                cancel_btn.click()
                time.sleep(1)
        except Exception as pe:
            log(f"알림 팝업 정리 중 특이사항 발생 (무시하고 계속 진행): {pe}")

        # 5단계: 카테고리 지정 시도
        if category and category.strip():
            log(f"5단계: 지정하신 카테고리 '{category}' 자동 맵핑 적용 시도...")
            category_success = False
            try:
                # 카테고리 선택 영역 버튼 클릭
                category_btn = page.query_selector("button.se-editor-category-selector-button, .se-category-container button, .se-document-category")
                if category_btn:
                    category_btn.click()
                    time.sleep(1.5)
                    
                    # 드롭다운 내부 카테고리 텍스트 스캔
                    items = page.locator(".se-editor-category-selector-list .se-select-item, .se-category-list .se-category-item, .se-select-list .se-select-item")
                    count = items.count()
                    for idx in range(count):
                        item = items.nth(idx)
                        txt = item.inner_text()
                        if category.strip() in txt:
                            log(f"일치 카테고리 탐색 성공 ➡️ '{txt}' 클릭")
                            item.click()
                            category_success = True
                            time.sleep(1)
                            break
                            
                    if not category_success:
                        # 차선책 텍스트 직접 매칭 클릭
                        page.locator(f'text="{category.strip()}"').first.click()
                        category_success = True
                        log(f"카테고리 텍스트 직접 클릭 성공: '{category}'")
                        time.sleep(1)
                else:
                    log("카테고리 선택 조작 버튼을 찾을 수 없습니다. 수동 지정이 요구됩니다.")
            except Exception as ce:
                log(f"카테고리 매칭 처리 중 실패 (무시하고 계속 진행): {ce}")
                try:
                    page.keyboard.press("Escape")
                except:
                    pass

        # 6단계: 제목 자동 입력 (fill API 사용으로 클립보드 미오염)
        log("6단계: 제목 입력란 탐색 및 자동 기입...")
        title_injected = False
        try:
            title_textarea = page.query_selector("textarea.se-textarea")
            if title_textarea:
                title_textarea.click()
                time.sleep(0.5)
                # 직접 값을 밀어 넣어 안정성 극대화
                page.fill("textarea.se-textarea", title)
                title_injected = True
                log("제목 텍스트 주입 완료")
                time.sleep(0.5)
            else:
                log("제목 입력 컴포넌트(textarea.se-textarea)를 찾을 수 없습니다.")
        except Exception as te:
            log(f"제목 기입 도중 실패: {te}")

        # 7단계: 본문 자동 입력 (하이퍼링크 활성화된 HTML 형태로 안전 주입)
        log("7단계: 본문 입력 영역 탐색 및 하이퍼링크 리치 HTML 주입 시작...")
        content_injected = False
        try:
            content_div = page.query_selector(".se-content")
            if content_div:
                content_div.click()
                time.sleep(0.5)
                
                # 기존 찌꺼기 텍스트 전체 선택 후 제거
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                time.sleep(0.5)
                
                # 텍스트를 HTML 포맷(하이퍼링크가 구현된 상태)으로 변환
                html_body = convert_text_to_html_with_links(content)
                
                # 브라우저 내부 execCommand 'insertHTML' API를 활용해
                # 클립보드를 건드리지 않고 파랗게 링크 밑줄이 활성화된 상태로 본문 즉시 주입!
                page.evaluate("html => { document.execCommand('insertHTML', false, html); }", html_body)
                content_injected = True
                log("본문 리치 HTML(링크 활성화 형태) 주입 성공!")
                time.sleep(1.5)
            else:
                log("본문 입력 컴포넌트(.se-content)를 찾을 수 없습니다.")
        except Exception as be:
            log(f"본문 HTML 주입 도중 실패: {be}")

        # 8단계: 해시태그 자동 등록
        if tags:
            log("8단계: 하단 해시태그 영역 탐색 및 입력 중...")
            try:
                tag_input = page.query_selector(".se-tag-input")
                if tag_input:
                    tag_input.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    for tag in tags:
                        tag_input.click()
                        time.sleep(0.2)
                        # 개별 태그 입력 후 엔터 처리하여 등록
                        page.fill(".se-tag-input", tag.strip())
                        time.sleep(0.2)
                        page.keyboard.press("Enter")
                        time.sleep(0.3)
                    log("해시태그 자동 입력 완료")
                else:
                    log("태그 입력 도구(.se-tag-input)를 찾을 수 없어 입력을 스킵합니다.")
            except Exception as tge:
                log(f"태그 입력 과정 중 일부 예외 발생(무시): {tge}")

        # 9단계: 발행 버튼 회피 및 임시저장(저장) 버튼 자동화
        log("9단계: 임시저장(저장) 버튼 자동 트리거 시도...")
        save_success = False
        try:
            save_btn = page.query_selector(".se-btn-save")
            if save_btn:
                save_btn.click()
                log("저장 버튼 클릭 이벤트 전송 완료. 데이터 동기화 대기 중...")
                time.sleep(3) # 저장 데이터가 서버로 전송 완료될 때까지 안전 대기
                save_success = True
            else:
                log("임시저장 버튼(.se-btn-save)을 찾지 못했습니다.")
        except Exception as se:
            log(f"임시저장 처리 중 에러 발생: {se}")

        # 10단계: 성공 및 예외 가이드 분기
        # 주요 요소 중 하나라도 누락되거나 실패했다면 수동 안내를 위해 브라우저를 켜둔다.
        if not (title_injected and content_injected and save_success):
            log("⚠ 일부 조작 단계(제목/본문 주입 또는 임시저장 클릭)가 정상 완수되지 않았습니다. 수동 지침 모드를 기동합니다.")
            return {
                "success": False,
                "message": "스마트에디터 로딩 지연 또는 화면 구조 변형으로 인해 자동 작성이 일부 미완수되었습니다. 열린 브라우저 창에서 마저 입력해 주세요.",
                "manual_mode": True,
                "playwright_instance": p,
                "context_instance": browser_context
            }

        log("🎉 모든 단계가 성공적으로 이행되어 임시저장이 완료되었습니다! 브라우저를 정리합니다.")
        browser_context.close()
        p.stop()
        
        return {"success": True, "message": "네이버 블로그 스마트에디터 임시저장이 성공적으로 완료되었습니다!"}
        
    except Exception as overall_e:
        log(f"💥 자동화 구동 모듈 심각한 크래시 발생: {overall_e}")
        # 크래시 발생 시에도 사용자가 붙여넣을 수 있게 브라우저 세션을 절대 끄지 않고 리턴
        return {
            "success": False,
            "message": f"시스템 조작 중 에러 발생: {str(overall_e)}. 열려 있는 크롬 창에서 직접 작성을 진행해 주세요.",
            "manual_mode": True,
            "playwright_instance": p,
            "context_instance": browser_context
        }
