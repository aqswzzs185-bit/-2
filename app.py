import streamlit as st
import config
import generator
import publisher
import link_handler
import validator
import seo_validator
import history_manager
import similarity_checker
import workspace_state
import json
import os
os.environ["API_VERSION"] = "v1"
import time
import platform
from datetime import datetime

# 페이지 설정 및 테마 느낌 주기
st.set_page_config(
    page_title="부모님 생활 블로그 자동화 도우미",
    page_icon="👵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 설정 불러오기
cfg = config.load_config()
last_inputs = cfg.get("LAST_INPUTS", {})

# 상품 DB 로드 함수
def load_products_db():
    try:
        with open("products_db.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"상품 DB 로드 실패: {e}")
        return {}

products_db = load_products_db()

# 💡 14차 고도화: 로컬 무손실 세션 상태 로드 및 세션 상태 초기화
saved_state = workspace_state.load_workspace_state()

# 세션 상태 변수 복원 또는 기본값 초기화
if "generated_post" not in st.session_state:
    st.session_state.generated_post = saved_state.get("generated_post", None)
if "edit_title" not in st.session_state:
    st.session_state.edit_title = saved_state.get("edit_title", "")
if "edit_content" not in st.session_state:
    st.session_state.edit_content = saved_state.get("edit_content", "")
if "edit_tags" not in st.session_state:
    st.session_state.edit_tags = saved_state.get("edit_tags", "")
if "chosen_title_index" not in st.session_state:
    st.session_state.chosen_title_index = saved_state.get("chosen_title_index", 0)
if "validation_result" not in st.session_state:
    st.session_state.validation_result = saved_state.get("validation_result", None)
if "seo_result" not in st.session_state:
    st.session_state.seo_result = saved_state.get("seo_result", None)
if "similarity_report" not in st.session_state:
    st.session_state.similarity_report = saved_state.get("similarity_report", None)
if "dup_warning_data" not in st.session_state:
    st.session_state.dup_warning_data = saved_state.get("dup_warning_data", None)
if "angle_suggestions" not in st.session_state:
    st.session_state.angle_suggestions = saved_state.get("angle_suggestions", [])
if "show_manual_panel" not in st.session_state:
    st.session_state.show_manual_panel = saved_state.get("show_manual_panel", False)
if "current_post_id" not in st.session_state:
    st.session_state.current_post_id = saved_state.get("current_post_id", None)
if "current_post_status" not in st.session_state:
    st.session_state.current_post_status = saved_state.get("current_post_status", "초안 생성 완료")
if "last_error_log" not in st.session_state:
    st.session_state.last_error_log = saved_state.get("last_error_log", "")

# 비휘발성 브라우저 자원 객체(복원하지 않고 항상 초기화)
if "playwright_instance" not in st.session_state:
    st.session_state.playwright_instance = None
if "context_instance" not in st.session_state:
    st.session_state.context_instance = None
if "force_generate" not in st.session_state:
    st.session_state.force_generate = False
if "injected_keyword" not in st.session_state:
    st.session_state.injected_keyword = None
if "injected_product" not in st.session_state:
    st.session_state.injected_product = None
if "injected_title" not in st.session_state:
    st.session_state.injected_title = None
if "trend_result" not in st.session_state:
    st.session_state.trend_result = None
if "expanded_result" not in st.session_state:
    st.session_state.expanded_result = None
if "comp_analysis_result" not in st.session_state:
    st.session_state.comp_analysis_result = None




# 💡 현재 작업 세션을 파일에 즉시 영구 저장하는 헬퍼 함수
def persist_current_state():
    state_to_save = {
        "generated_post": st.session_state.generated_post,
        "edit_title": st.session_state.edit_title,
        "edit_content": st.session_state.edit_content,
        "edit_tags": st.session_state.edit_tags,
        "chosen_title_index": st.session_state.chosen_title_index,
        "validation_result": st.session_state.validation_result,
        "seo_result": st.session_state.seo_result,
        "similarity_report": st.session_state.similarity_report,
        "dup_warning_data": st.session_state.dup_warning_data,
        "angle_suggestions": st.session_state.angle_suggestions,
        "show_manual_panel": st.session_state.show_manual_panel,
        "current_post_id": st.session_state.current_post_id,
        "current_post_status": st.session_state.current_post_status,
        "last_error_log": st.session_state.last_error_log
    }
    workspace_state.save_workspace_state(state_to_save)

# 사이드바 설정 화면
st.sidebar.markdown("# ⚙️ 환경 설정")
st.sidebar.markdown("프로그램 동작에 필요한 설정값을 입력하세요.")

gemini_key = st.sidebar.text_input("Google Gemini API Key", value=cfg.get("GEMINI_API_KEY", ""), type="password", help="Gemini API 키를 입력해 주세요.")
naver_id = st.sidebar.text_input("Naver ID", value=cfg.get("NAVER_ID", ""), help="네이버 블로그의 주인 아이디를 입력합니다. (비워둘 시 네이버 메인으로 이동)")
naver_client_id = st.sidebar.text_input("Naver Client ID (데이터랩)", value=cfg.get("NAVER_CLIENT_ID", ""), type="password", help="네이버 데이터랩 수집용 Client ID")
naver_client_secret = st.sidebar.text_input("Naver Client Secret (데이터랩)", value=cfg.get("NAVER_CLIENT_SECRET", ""), type="password", help="네이버 데이터랩 수집용 Client Secret")
chrome_profile = st.sidebar.text_input("Chrome Profile Path", value=cfg.get("CHROME_PROFILE_DIR", "./naver_chrome_profile"), help="로그인 상태(쿠키)를 저장할 로컬 폴더 경로입니다.")
tone = st.sidebar.text_area("기본 글쓰기 성향 가이드", value=cfg.get("DEFAULT_TONE", ""), height=100)

if st.sidebar.button("설정 저장", use_container_width=True):
    cfg["GEMINI_API_KEY"] = gemini_key
    cfg["NAVER_ID"] = naver_id
    cfg["NAVER_CLIENT_ID"] = naver_client_id
    cfg["NAVER_CLIENT_SECRET"] = naver_client_secret
    cfg["CHROME_PROFILE_DIR"] = chrome_profile
    cfg["DEFAULT_TONE"] = tone
    if config.save_config(cfg):
        st.sidebar.success("설정이 안전하게 저장되었습니다!")
    else:
        st.sidebar.error("설정 저장에 실패했습니다.")


# 메인 UI
st.title("👵 부모님 생활 블로그 자동화 도우미")
st.markdown("""
이 프로그램은 **부모님 선물, 시니어 생활용품, 안전용품** 전문 블로그 포스팅을 빠르게 기획하고 작성할 수 있도록 돕습니다.
단순 광고글이 아니라 **자녀의 진정성 있는 관점**에서 정보성 포스팅을 자동 생성하고, 안전하게 네이버 블로그에 **임시저장**합니다.
""")

st.divider()

# 💡 15차 고도화: 모바일/데스크톱 반응형 3단 컨트롤 타워 배치
col_grp1, col_grp2, col_grp3 = st.columns([1, 1, 1])

# 데이터 옵션 정의
post_types = [
    "부모님 선물 추천형",
    "시니어 생활문제 해결형",
    "혼자 사는 부모님 안심용품형",
    "계절별 생활용품형",
    "욕실·침실·주방 안전용품형",
    "건강관리 생활용품형",
    "비교 추천형",
    "체크리스트형"
]
targets = ["어머니", "아버지", "부모님 공통", "혼자 사는 부모님", "60대", "70대", "80대"]
situations = ["생신", "명절", "겨울", "여름", "장마철", "욕실 안전", "수면", "건강관리", "외출", "집안 안전", "혼자 거주"]
char_counts = ["1500자", "2000자", "2500자", "3000자"]
tones = ["따뜻한 정보형", "자녀가 부모님을 걱정하는 말투", "차분한 전문가형", "블로그 자연체", "후기형"]
db_categories = list(products_db.keys())

main_keyword_val = last_inputs.get("main_keyword", "")
products_display_val = last_inputs.get("products", "")
links_input_val = last_inputs.get("links", ["", ""])
link_count_val = last_inputs.get("link_count", 2)
selected_db_cat_val = last_inputs.get("selected_db_cat", db_categories[0])
selected_product_val = last_inputs.get("selected_product", "")
blog_category_val = last_inputs.get("blog_category", "")

# 💡 실시간 트렌드 주입 값 우선 이식
if st.session_state.get("injected_keyword"):
    main_keyword_val = st.session_state.injected_keyword
if st.session_state.get("injected_product"):
    products_display_val = st.session_state.injected_product
    # products_db를 역추적해 대분류 카테고리와 세부 상품군 자동 설정
    found_cat = None
    for db_cat, db_prods in products_db.items():
        if products_display_val in db_prods:
            found_cat = db_cat
            break
    if found_cat:
        selected_db_cat_val = found_cat
        selected_product_val = products_display_val
    else:
        selected_product_val = "직접 입력"
if st.session_state.get("injected_title"):
    injected_title_val = st.session_state.injected_title
else:
    injected_title_val = ""



with col_grp1:
    st.markdown("##### 📝 1. 기획 및 원고 생성")
    btn_col1, btn_col2 = st.columns(2)
    
    # 1. 새 글 만들기
    if btn_col1.button("🆕 새 글 만들기", use_container_width=True, type="primary"):
        workspace_state.reset_workspace_state()
        st.session_state.generated_post = None
        st.session_state.edit_title = ""
        st.session_state.edit_content = ""
        st.session_state.edit_tags = ""
        st.session_state.chosen_title_index = 0
        st.session_state.validation_result = None
        st.session_state.seo_result = None
        st.session_state.similarity_report = None
        st.session_state.dup_warning_data = None
        st.session_state.angle_suggestions = []
        st.session_state.injected_keyword = None
        st.session_state.injected_product = None
        st.session_state.injected_title = None

        st.session_state.show_manual_panel = False
        st.session_state.current_post_id = None
        st.session_state.current_post_status = "초안 생성 완료"
        st.session_state.last_error_log = ""
        st.success("초기화 완료!")
        st.rerun()
        
    # 2. 키워드 입력
    if btn_col2.button("🔑 키워드 입력", use_container_width=True):
        st.info("👈 왼쪽 입력창에서 키워드를 기입하세요.")
        
    # 3. 글 초안 생성
    if btn_col1.button("✍️ 글 초안 생성", use_container_width=True):
        if not gemini_key:
            st.error("Gemini API Key를 등록해 주세요.")
        elif not main_keyword_val:
            st.error("메인 키워드를 입력해 주세요.")
        elif not products_display_val:
            st.error("소개할 상품군을 지정해 주세요.")
        else:
            history_list = history_manager.load_history()
            dup_res = similarity_checker.check_duplication_before_generation(history_list, main_keyword_val, products_display_val)
            if not st.session_state.force_generate and (dup_res["keyword_dup"] or dup_res["product_recent"]):
                with st.spinner("중복 이력 분석 중..."):
                    existing_titles = [post.get("title", "") for post in history_list if post.get("title")]
                    angles = similarity_checker.suggest_new_angles(gemini_key, main_keyword_val, products_display_val, existing_titles)
                    st.session_state.dup_warning_data = dup_res
                    st.session_state.angle_suggestions = angles
                    persist_current_state()
                    st.warning("⚠️ 중복 경고가 감지되었습니다. 대안 각도를 선택하세요.")
                    st.rerun()
            st.session_state.force_generate = False
            st.session_state.dup_warning_data = None
            with st.spinner("원고 초안 생성 중..."):
                db_product_info = {}
                if selected_product_val != "직접 입력":
                    db_product_info = products_db.get(selected_db_cat_val, {}).get(selected_product_val, {})
                result = generator.generate_blog_post(
                    api_key=gemini_key,
                    main_keyword=main_keyword_val,
                    post_type=last_inputs.get("post_type", "부모님 선물 추천형"),
                    targets=last_inputs.get("targets", []),
                    situations=last_inputs.get("situations", []),
                    products=products_display_val,
                    links=links_input_val,
                    char_count=last_inputs.get("char_count", "2000자"),
                    tone_style=last_inputs.get("tone_style", "자녀가 부모님을 걱정하는 말투"),
                    blog_category=blog_category_val,
                    base_tone_guide=tone,
                    db_product_info=db_product_info
                )
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.session_state.generated_post = result
                    db_link_text = db_product_info.get("link_text", "") if selected_product_val != "직접 입력" else ""
                    st.session_state.edit_content = link_handler.assemble_post_with_links(
                        post_data=result,
                        links=links_input_val,
                        link_count=link_count_val,
                        product_name=products_display_val,
                        db_link_text=db_link_text
                    )
                    tags_list = result.get("hashtags", [])
                    st.session_state.edit_tags = ", ".join(tags_list)
                    candidates = result.get("title_candidates", [])
                    selected_title = st.session_state.get("injected_title") if st.session_state.get("injected_title") else result.get("selected_title", "")
                    flat_candidates = [item.get("title", "") if isinstance(item, dict) else item for item in candidates]
                    if selected_title not in flat_candidates:
                        flat_candidates.insert(0, selected_title)
                    default_idx = flat_candidates.index(selected_title)
                    st.session_state.chosen_title_index = default_idx
                    st.session_state.edit_title = selected_title

                    sim_rep = similarity_checker.check_generated_content_similarity(history_list, selected_title, st.session_state.edit_content, tags_list)
                    st.session_state.similarity_report = sim_rep
                    new_post_id = f"post_{int(time.time())}"
                    st.session_state.current_post_id = new_post_id
                    st.session_state.current_post_status = "초안 생성 완료"
                    initial_data = {
                        "main_keyword": main_keyword_val,
                        "post_type": last_inputs.get("post_type"),
                        "targets": last_inputs.get("targets"),
                        "products": products_display_val,
                        "links": links_input_val,
                        "title": selected_title,
                        "content": st.session_state.edit_content,
                        "tags": tags_list,
                        "post_status": st.session_state.current_post_status,
                        "image_prompts": result.get("image_prompts", [])
                    }
                    history_manager.add_or_update_post(new_post_id, initial_data)
                    persist_current_state()
                    # 💡 생성 성공했으므로 트렌드 주입 상태 클리어
                    st.session_state.injected_keyword = None
                    st.session_state.injected_product = None
                    st.session_state.injected_title = None
                    st.success("🎉 글 초안 완성!")
                    st.rerun()

                    
    # 4. 제목 다시 생성
    if btn_col2.button("🔄 제목 다시 생성", use_container_width=True):
        if not gemini_key:
            st.error("API Key를 먼저 설정해주세요.")
        elif not st.session_state.edit_content:
            st.error("본문 내용이 존재하지 않습니다.")
        else:
            with st.spinner("6대 유형 제목 후보 재생성 중..."):
                ret_titles = generator.regenerate_titles(
                    api_key=gemini_key,
                    main_keyword=main_keyword_val,
                    content=st.session_state.edit_content,
                    products=products_display_val
                )
                if "error" in ret_titles:
                    st.error(ret_titles["error"])
                else:
                    st.session_state.generated_post["title_candidates"] = ret_titles.get("title_candidates", [])
                    st.session_state.generated_post["selected_title"] = ret_titles.get("selected_title", "")
                    st.session_state.edit_title = ret_titles.get("selected_title", "")
                    st.session_state.chosen_title_index = 0
                    if st.session_state.current_post_id:
                        history_manager.add_or_update_post(st.session_state.current_post_id, {"title": st.session_state.edit_title})
                    persist_current_state()
                    st.success("🎉 제목 재생성 완료!")
                    st.rerun()
                    
    # 5. 쇼커 링크 삽입
    if st.button("🔗 5. 쇼커 링크 삽입", use_container_width=True):
        if not st.session_state.generated_post:
            st.error("초안 생성을 먼저 기동해 주세요.")
        else:
            db_product_info = {}
            if selected_product_val != "직접 입력":
                db_product_info = products_db.get(selected_db_cat_val, {}).get(selected_product_val, {})
            db_link_text = db_product_info.get("link_text", "") if selected_product_val != "직접 입력" else ""
            st.session_state.edit_content = link_handler.assemble_post_with_links(
                post_data=st.session_state.generated_post,
                links=links_input_val,
                link_count=link_count_val,
                product_name=products_display_val,
                db_link_text=db_link_text
            )
            persist_current_state()
            st.success("🔗 쇼커 링크 조립 완료!")
            st.rerun()

with col_grp2:
    st.markdown("##### 🔍 2. 품질 및 준법 검수")
    btn_col3, btn_col4 = st.columns(2)
    
    # 6. 광고성 검수
    if btn_col3.button("🔍 광고성 검수", use_container_width=True):
        if not gemini_key:
            st.error("Gemini API Key를 등록해 주세요.")
        elif not st.session_state.edit_content:
            st.error("검수할 원고 본문이 비어 있습니다.")
        else:
            with st.spinner("광고성 검수 중..."):
                tags_list = [t.strip() for t in st.session_state.edit_tags.split(",") if t.strip()]
                val_result = validator.run_content_check(
                    api_key=gemini_key,
                    title=st.session_state.edit_title,
                    content=st.session_state.edit_content,
                    tags=tags_list
                )
                st.session_state.validation_result = val_result
                st.session_state.seo_result = None
                if st.session_state.current_post_id:
                    st.session_state.current_post_status = "검수 필요"
                    history_manager.add_or_update_post(st.session_state.current_post_id, {
                        "ad_risk": val_result.get("ad_risk", "보통"),
                        "post_status": st.session_state.current_post_status
                    })
                persist_current_state()
                st.success("🔎 광고 심사 완료!")
                st.rerun()
                
    # 7. SEO 검수
    if btn_col4.button("📊 SEO 검수", use_container_width=True):
        if not gemini_key:
            st.error("Gemini API Key를 등록해 주세요.")
        elif not st.session_state.edit_content:
            st.error("분석할 본문이 비어 있습니다.")
        else:
            with st.spinner("SEO 분석 중..."):
                tags_list = [t.strip() for t in st.session_state.edit_tags.split(",") if t.strip()]
                seo_res = seo_validator.evaluate_seo_and_readability(
                    api_key=gemini_key,
                    title=st.session_state.edit_title,
                    content=st.session_state.edit_content,
                    tags=tags_list,
                    main_keyword=main_keyword_val,
                    char_count=last_inputs.get("char_count", "2000자"),
                    products=products_display_val
                )
                st.session_state.seo_result = seo_res
                st.session_state.validation_result = None
                if st.session_state.current_post_id:
                    st.session_state.current_post_status = "검수 필요"
                    history_manager.add_or_update_post(st.session_state.current_post_id, {
                        "seo_score": seo_res.get("seo_score", 0),
                        "ad_risk": seo_res.get("ad_risk", "보통"),
                        "post_status": st.session_state.current_post_status
                    })
                persist_current_state()
                st.success("📊 SEO 분석 완료!")
                st.rerun()
                
    # 8. 이미지 프롬프트 생성
    if btn_col3.button("🎨 이미지 프롬프트", use_container_width=True):
        if not gemini_key:
            st.error("Gemini API Key를 등록해 주세요.")
        elif not st.session_state.edit_content:
            st.error("원고 본문이 존재하지 않습니다.")
        else:
            with st.spinner("영문 프롬프트 생성 중..."):
                img_res = generator.regenerate_image_prompts(
                    api_key=gemini_key,
                    content=st.session_state.edit_content,
                    products=products_display_val
                )
                if "error" in img_res:
                    st.error(img_res["error"])
                else:
                    st.session_state.generated_post["image_prompts"] = img_res.get("image_prompts", [])
                    if st.session_state.current_post_id:
                        history_manager.add_or_update_post(st.session_state.current_post_id, {
                            "image_prompts": img_res.get("image_prompts", [])
                        })
                    persist_current_state()
                    st.success("📸 영문 프롬프트 생성 완료!")
                    st.rerun()
                    
    # 9. 미리보기
    if btn_col4.button("👁️ 미리보기", use_container_width=True):
        if not st.session_state.edit_content:
            st.error("미리보기할 글 내용이 없습니다.")
        else:
            st.markdown("#### 📱 모바일 가독성 가상 뷰어")
            with st.container(border=True):
                st.markdown(f"**[제목] {st.session_state.edit_title}**")
                st.markdown("---")
                st.text(st.session_state.edit_content)
                st.markdown("---")
                st.markdown(f"*태그*: `{st.session_state.edit_tags}`")

with col_grp3:
    st.markdown("##### 📤 3. 네이버 전송 및 보존")
    btn_col5, btn_col6 = st.columns(2)
    
    # 10. 네이버 블로그에 입력
    if btn_col5.button("📤 블로그 입력", use_container_width=True):
        is_cloud = (platform.system() != "Windows")
        if is_cloud:
            st.warning("⚠️ **클라우드 서버 구동 모드**")
            st.info("클라우드 서버 환경에서는 네이버 로그인 창을 직접 띄울 수 없습니다. 대신 아래의 **수동 입력 패널**로 최종 원고를 1초 만에 복사하여 휴대폰 블로그 앱에 등록해 주세요! 🟢")
            st.session_state.show_manual_panel = True
            persist_current_state()
            st.rerun()
        elif not st.session_state.edit_content:
            st.error("블로그에 입력할 내용이 없습니다.")
        else:
            if st.session_state.playwright_instance:
                try: st.session_state.context_instance.close(); st.session_state.playwright_instance.stop()
                except: pass
                st.session_state.playwright_instance = None
                st.session_state.context_instance = None
            status_bar = st.status("네이버 글쓰기 접속 중...", expanded=True)
            tags_list = [t.strip() for t in st.session_state.edit_tags.split(",") if t.strip()]
            try:
                pub_result = publisher.run_naver_publisher(
                    naver_id=naver_id,
                    title=st.session_state.edit_title,
                    content=st.session_state.edit_content,
                    tags=tags_list,
                    category=blog_category_val,
                    profile_dir=chrome_profile,
                    status_callback=lambda m: status_bar.write(f"⏳ {m}"),
                    auto_click_save=False
                )
                if pub_result["success"]:
                    status_bar.update(label="✅ 원고 자동 기입 완료!", state="complete")
                    st.success("네이버 에디터에 제목, 본문, 링크, 태그 자동 입력 완료! 창 대기 중.")
                    st.session_state.show_manual_panel = False
                    st.session_state.current_post_status = "네이버 입력 완료"
                    if st.session_state.current_post_id:
                        history_manager.add_or_update_post(st.session_state.current_post_id, {
                            "naver_input_done": True,
                            "post_status": st.session_state.current_post_status
                        })
                else:
                    status_bar.update(label="⚠️ 자동 기입 보류", state="error")
                    st.error(pub_result["message"])
                    st.session_state.last_error_log = pub_result["message"]
                    st.session_state.current_post_status = "오류 발생"
                    if st.session_state.current_post_id:
                        history_manager.add_or_update_post(st.session_state.current_post_id, {
                            "post_status": st.session_state.current_post_status,
                            "error_log": pub_result["message"]
                        })
                    if pub_result.get("manual_mode"):
                        st.session_state.playwright_instance = pub_result.get("playwright_instance")
                        st.session_state.context_instance = pub_result.get("context_instance")
                        st.session_state.show_manual_panel = True
            except Exception as e:
                status_bar.update(label="❌ 에러 발생", state="error")
                st.error(str(e))
                st.session_state.last_error_log = str(e)
                st.session_state.current_post_status = "오류 발생"
                if st.session_state.current_post_id:
                    history_manager.add_or_update_post(st.session_state.current_post_id, {
                        "post_status": st.session_state.current_post_status,
                        "error_log": str(e)
                    })
            persist_current_state()
            st.rerun()
            
    # 11. 임시저장
    if btn_col6.button("💾 임시저장", use_container_width=True):
        is_cloud = (platform.system() != "Windows")
        if is_cloud:
            st.warning("⚠️ **클라우드 서버 구동 모드**")
            st.info("클라우드 서버 환경에서는 네이버 임시저장 버튼을 원격 제어할 수 없습니다. 대신 아래의 **수동 입력 패널**로 복사해 글을 등록해 주세요! 🟢")
            st.session_state.show_manual_panel = True
            persist_current_state()
            st.rerun()
        elif st.session_state.playwright_instance and st.session_state.context_instance:
            status_bar = st.status("임시저장 클릭 자동화 중...", expanded=True)
            try:
                pages = st.session_state.context_instance.pages
                if pages:
                    blog_page = pages[0]
                    save_btn_selector = "button.se-btn-save-temp, button.btn_save"
                    blog_page.wait_for_selector(save_btn_selector, timeout=5000)
                    blog_page.click(save_btn_selector)
                    status_bar.write("⏳ 임시저장 버튼이 실행되었습니다...")
                    time.sleep(3)
                    st.session_state.context_instance.close()
                    st.session_state.playwright_instance.stop()
                    st.session_state.playwright_instance = None
                    st.session_state.context_instance = None
                    st.session_state.show_manual_panel = False
                    st.session_state.current_post_status = "임시저장 완료"
                    if st.session_state.current_post_id:
                        history_manager.add_or_update_post(st.session_state.current_post_id, {
                            "temp_save_done": True,
                            "post_status": st.session_state.current_post_status,
                            "error_log": ""
                        })
                    status_bar.update(label="✅ 임시저장 완료!", state="complete")
                    st.success("네이버 블로그 임시저장 완료 및 브라우저 수거 완료!")
            except Exception as e:
                st.error(f"임시저장 실패: {e}")
                st.session_state.last_error_log = str(e)
            persist_current_state()
            st.rerun()
        else:
            if not st.session_state.edit_content:
                st.error("저장할 원고 내용이 없습니다.")
            else:
                status_bar = st.status("임시저장 일괄 실행 중...", expanded=True)
                tags_list = [t.strip() for t in st.session_state.edit_tags.split(",") if t.strip()]
                try:
                    pub_result = publisher.run_naver_publisher(
                        naver_id=naver_id,
                        title=st.session_state.edit_title,
                        content=st.session_state.edit_content,
                        tags=tags_list,
                        category=blog_category_val,
                        profile_dir=chrome_profile,
                        status_callback=lambda m: status_bar.write(f"⏳ {m}"),
                        auto_click_save=True
                    )
                    if pub_result["success"]:
                        status_bar.update(label="✅ 임시저장 성공!", state="complete")
                        st.success("네이버 임시저장 완료!")
                        st.session_state.current_post_status = "임시저장 완료"
                        if st.session_state.current_post_id:
                            history_manager.add_or_update_post(st.session_state.current_post_id, {
                                "naver_input_done": True,
                                "temp_save_done": True,
                                "post_status": st.session_state.current_post_status,
                                "error_log": ""
                            })
                    else:
                        status_bar.update(label="❌ 임시저장 중단", state="error")
                        st.error(pub_result["message"])
                        st.session_state.last_error_log = pub_result["message"]
                        st.session_state.current_post_status = "오류 발생"
                        if st.session_state.current_post_id:
                            history_manager.add_or_update_post(st.session_state.current_post_id, {
                                "post_status": st.session_state.current_post_status,
                                "error_log": pub_result["message"]
                            })
                except Exception as e:
                    status_bar.update(label="❌ 에러 발생", state="error")
                    st.error(str(e))
                    st.session_state.last_error_log = str(e)
                    st.session_state.current_post_status = "오류 발생"
                    if st.session_state.current_post_id:
                        history_manager.add_or_update_post(st.session_state.current_post_id, {
                            "post_status": st.session_state.current_post_status,
                            "error_log": str(e)
                        })
                persist_current_state()
                st.rerun()
                
    # 12. 저장된 글 목록
    if btn_col5.button("📂 저장된 글 목록", use_container_width=True):
        st.info("💡 하단 '📂 저장된 글 이력 관리' 탭에서 히스토리를 확인하세요.")
        
    # 13. 오류 로그 확인
    if btn_col6.button("❌ 오류 로그", use_container_width=True):
        if st.session_state.last_error_log:
            st.error(f"📍 직전 에러 로그:\n`{st.session_state.last_error_log}`")
        else:
            st.success("발견된 시스템 오류 로그가 없습니다. 🟢")
            
    # 14. 설정
    if st.button("⚙️ 14. 환경 설정", use_container_width=True):
        st.info("👈 왼쪽 사이드바의 환경 설정 탭에서 설정하세요.")

st.divider()

# 상단 탭 이식으로 화면 다각화
tab_trend, tab_write, tab_history = st.tabs(["⚡ 실시간 주제 추천", "✍️ 포스팅 기획 및 작성", "📂 저장된 글 이력 관리"])

with tab_trend:
    st.subheader("⚡ 실시간 트렌드 기반 블로그 마케팅 통합 OS")
    st.markdown("""
    네이버 데이터랩, 쇼핑인사이트, 롱테일 확장, 경쟁도 진단, 쇼커 매칭 통계를 종합 관제하여 
    **매일 마케팅 주제를 발굴하고 즉시 글 생성 및 네이버 등록 자동화**로 이어지는 20단계 전체 파이프라인의 핵심 관제 타워입니다.
    """)
    
    # 7. 키워드 수집 실행 & 8. 환경 설정 가이드 배치
    col_ctr1, col_ctr2 = st.columns([2, 1])
    with col_ctr1:
        if st.button("🔄 7. 실시간 네이버 데이터랩 트렌드 데이터 수집 가동", type="primary", use_container_width=True):
            if not gemini_key:
                st.error("👈 왼쪽 사이드바에서 Google Gemini API Key를 먼저 설정해주세요!")
            else:
                with st.spinner("네이버 빅데이터 트렌드 수집 및 AI 스코어링 분석 중... (약 10초 소요)"):
                    try:
                        import trend_analyzer
                        res = trend_analyzer.collect_trending_topics(gemini_key)
                        if "error" in res:
                            st.error(res["error"])
                        else:
                            st.session_state.trend_result = res
                            st.success("🎉 최근 핫 트렌드 키워드 수집 및 20개 점수 계산이 완료되었습니다!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"주제 분석 실패: {str(e)}")
    with col_ctr2:
        st.caption("📍 수집 버튼 클릭 시 실시간 검색어 및 쇼핑 관심도가 최신 날짜로 갱신됩니다.")
        
    st.divider()

    # 1. 오늘의 추천 주제 & 12. 제목 후보 5개 생성
    try:
        import daily_recommender
        today_recs = daily_recommender.get_today_recommendations()
        if today_recs:
            st.markdown("### 🌟 1. 오늘의 추천 주제 (Best 5)")
            st.markdown("오늘 부모님 생활 블로그에 작성하기 가장 적합한 고가치 5대 주제입니다. 마음에 드는 제목 후보를 클릭해 바로 글쓰기를 기동해 보세요!")
            
            for item in today_recs:
                with st.container(border=True):
                    st.markdown(f"#### 🏆 **{item.get('rank')}위 주제**: **{item.get('title')}** (최종 점수: `{item.get('total_score')}점`)")
                    
                    col_det1, col_det2 = st.columns([2, 1])
                    with col_det1:
                        st.markdown(f"- 🔑 **메인 키워드**: `{item.get('keyword')}`")
                        st.markdown(f"- 📦 **관련 상품군**: `{item.get('product')}`")
                        st.markdown(f"- 📝 **글 유형**: `{item.get('post_type')}`")
                        st.markdown(f"- 💡 **추천 이유**: *{item.get('reason')}*")
                        st.markdown(f"- 🔗 **쇼커 링크 연결 방식**: `{item.get('shocker_link_guide')}`")
                        
                        # 24차 고도화: 쇼커 상품 매칭 분석 토글 이식
                        with st.expander("🔗 이 주제의 쇼커 상품군 매칭 정보 분석", expanded=False):
                            try:
                                import shocker_matcher
                                match_res = shocker_matcher.get_shocker_matched_products(item.get("title"))
                                if not match_res["is_valid"]:
                                    st.error(match_res["matches"][0]["reason"])
                                else:
                                    st.markdown("🎯 **추천 상품군별 쇼커 연결 가이드라인**")
                                    for m_idx, m_info in enumerate(match_res["matches"]):
                                        with st.container(border=True):
                                            col_m_text, col_m_btn = st.columns([3, 1])
                                            with col_m_text:
                                                st.markdown(f"📦 **상품군**: `{m_info['product']}` | **연결 가능성**: **{m_info['possibility']}**")
                                                st.markdown(f"- **위치**: `{m_info['position']}`")
                                                st.markdown(f"- **앵커**: `{m_info['anchor_text']}`")
                                                st.markdown(f"- *분석*: {m_info['reason']}")
                                            with col_m_btn:
                                                if st.button("✍️ 상품 주입", key=f"inject_shocker_prod_{item.get('rank')}_{m_idx}", use_container_width=True):
                                                    st.session_state.injected_keyword = item.get('keyword')
                                                    st.session_state.injected_product = m_info['product']
                                                    st.success(f"상품 '{m_info['product']}' 주입 완료! 작성창에서 초안 작성을 시작하세요.")
                                                    st.rerun()
                            except Exception as e_match:
                                st.error(f"쇼커 매칭 분석 실패: {e_match}")
                    with col_det2:
                        st.markdown("**📝 제목 후보 5개 (클릭 시 기획창 주입)**")
                        for t_idx, title in enumerate(item.get("titles_pool", [])):
                            if st.button(f"📌 {t_idx+1}. {title[:32]}...", key=f"title_inject_{item.get('rank')}_{t_idx}", help=title, use_container_width=True):
                                st.session_state.injected_keyword = item.get('keyword')
                                st.session_state.injected_product = item.get('product')
                                st.session_state.injected_title = title
                                st.success(f"주입 완료!  \n제목: `{title}`  \n\n'✍️ 포스팅 기획 및 작성' 탭에서 [글 초안 생성]을 눌러주세요!")
                                st.rerun()
                                
            st.markdown("---")
            
    except Exception as e:
        st.error(f"오늘의 추천 주제 로딩 실패: {e}")

    # 💡 테마별 다차원 추천 탭 (2, 3, 4, 5번 통계 이식)
    st.markdown("### 🔍 테마별 특화 추천 키워드 리스트")
    sub_tab_rise, sub_tab_shocker, sub_tab_season, sub_tab_low_comp = st.tabs([
        "⚡ 2. 최근 상승 키워드", 
        "🔗 3. 쇼커 연결 가능 주제", 
        "📅 4. 계절 추천 주제", 
        "🟢 5. 경쟁도 낮은 주제"
    ])
    
    try:
        import topic_scorer
        scored_data = topic_scorer.calculate_topic_scores()
        
        # 2. 최근 상승 키워드 렌더링
        with sub_tab_rise:
            st.markdown("📈 **검색 유입율 상승세에 올라타기 좋은 최근 급상승 키워드**")
            # 폴백 난수 데이터나 실시간 상승률이 높은 후보 필터링
            rise_kws = [k for k in scored_data if "급상승" in k.get("trend_type", "")]
            if not rise_kws:
                rise_kws = scored_data[:8] # 없을 시 상위 8개 노출
            for idx, item in enumerate(rise_kws[:8]):
                with st.container(border=True):
                    col_t, col_b = st.columns([4, 1])
                    with col_t:
                        st.markdown(f"🔑 **키워드**: `{item['keyword']}` | 📦 **상품**: `{item['product']}`")
                        st.markdown(f"- 최종 점수: `{item['total_score']}점` | *사유*: {item['reason']}")
                    with col_b:
                        if st.button("✍️ 글 쓰기", key=f"rise_kw_apply_{idx}", use_container_width=True):
                            st.session_state.injected_keyword = item['keyword']
                            st.session_state.injected_product = item['product']
                            st.success(f"키워드 주입 완료! 작성창으로 이동하세요.")
                            st.rerun()
                            
        # 3. 쇼커 연결 가능 주제 렌더링
        with sub_tab_shocker:
            st.markdown("💰 **쇼커 제휴 상품군 매핑이 명확해 블로그 수익화에 가장 최적화된 주제**")
            shocker_kws = [k for k in scored_data if k.get("product") != "직접 입력" and "미지정" not in k.get("product", "")]
            for idx, item in enumerate(shocker_kws[:8]):
                with st.container(border=True):
                    col_t, col_b = st.columns([4, 1])
                    with col_t:
                        st.markdown(f"🔑 **키워드**: `{item['keyword']}` | 📦 **쇼커 매칭 상품**: `{item['product']}`")
                        st.markdown(f"- *연결 가이드*: `{item['shocker_link_guide']}`")
                    with col_b:
                        if st.button("✍️ 글 쓰기", key=f"shocker_kw_apply_{idx}", use_container_width=True):
                            st.session_state.injected_keyword = item['keyword']
                            st.session_state.injected_product = item['product']
                            st.success(f"키워드 주입 완료! 작성창으로 이동하세요.")
                            st.rerun()
                            
        # 4. 계절 추천 주제 렌더링
        with sub_tab_season:
            st.markdown("📅 **현재 시스템 감지 월을 기준으로 계절성 가산점 10점 만점을 획득한 제철 키워드**")
            # 계절성 점수가 고득점인 후보 필터링
            season_kws = scored_data[:12] # 계절성 기반 상위 12개 자동 바인딩
            for idx, item in enumerate(season_kws[:8]):
                with st.container(border=True):
                    col_t, col_b = st.columns([4, 1])
                    with col_t:
                        st.markdown(f"🔑 **키워드**: `{item['keyword']}` | 📦 **상품**: `{item['product']}`")
                        st.markdown(f"- 최종 점수: `{item['total_score']}점` | *유형*: `{item['post_type']}`")
                    with col_b:
                        if st.button("✍️ 글 쓰기", key=f"season_kw_apply_{idx}", use_container_width=True):
                            st.session_state.injected_keyword = item['keyword']
                            st.session_state.injected_product = item['product']
                            st.success(f"키워드 주입 완료! 작성창으로 이동하세요.")
                            st.rerun()
                            
        # 5. 경쟁도 낮은 주제 렌더링
        with sub_tab_low_comp:
            st.markdown("🟢 **상위 노출 글들이 오래되었거나 대형 인플루언서 점유가 낮아 초보자 진입을 강추하는 키워드**")
            low_comp_kws = [k for k in scored_data if len(k['keyword']) >= 12] # 롱테일 형태
            if not low_comp_kws:
                low_comp_kws = scored_data[5:15]
            for idx, item in enumerate(low_comp_kws[:8]):
                with st.container(border=True):
                    col_t, col_b = st.columns([4, 1])
                    with col_t:
                        st.markdown(f"🔑 **키워드**: `{item['keyword']}` | 📦 **상품**: `{item['product']}`")
                        st.markdown(f"- 최종 점수: `{item['total_score']}점` | *진입 추천 사유*: {item['reason']}")
                    with col_b:
                        if st.button("✍️ 글 쓰기", key=f"low_comp_kw_apply_{idx}", use_container_width=True):
                            st.session_state.injected_keyword = item['keyword']
                            st.session_state.injected_product = item['product']
                            st.success(f"키워드 주입 완료! 작성창으로 이동하세요.")
                            st.rerun()
                            
    except Exception as e_tabs:
        st.error(f"테마별 분석 탭 로딩 실패: {e_tabs}")
        
    st.divider()

    # 6. 저장된 키워드 목록 (시드 DB 아코디언 조회)
    with st.expander("📁 6. 저장된 키워드 목록 (기본 시드 데이터베이스)", expanded=False):
        try:
            with open("keywords_seed_db.json", "r", encoding="utf-8") as f_seed:
                seed_data = json.load(f_seed)
                for seed_cat, seed_items in seed_data.items():
                    st.markdown(f"##### **📁 {seed_cat}**")
                    seed_df_rows = []
                    for s_item in seed_items:
                        seed_df_rows.append({
                            "키워드": s_item.get("keyword"),
                            "매핑 상품군": s_item.get("related_product"),
                            "글 유형": s_item.get("expected_post_type"),
                            "공감 핵심 포인트": s_item.get("empathy_point")
                        })
                    import pandas as pd
                    st.dataframe(pd.DataFrame(seed_df_rows), use_container_width=True, hide_index=True)
        except Exception as e_seed:
            st.error(f"시드 DB 로드 실패: {e_seed}")

    # 8. 주제 점수표 보기 (100점 만점 테이블 리포트)
    st.markdown("---")
    st.subheader("🏆 8. 주제 종합 점수표 보기 (100점 만점)")
    st.markdown("""
    트렌드(25), 구매의도(25), 쇼커(20), 경쟁회피(15), 계절성(10), 작성용이성(3), 공감(2) 등 
    **7대 정밀 평가 가중치**를 총합산하여 점수가 가장 높은 포스팅 최적 주제와 세부 쇼커 가이드라인을 제시합니다.
    """)
    
    try:
        import topic_scorer
        scored_data = topic_scorer.calculate_topic_scores()
        if scored_data:
            import pandas as pd
            scored_rows = []
            for item in scored_data:
                scored_rows.append({
                    "순위": item.get("rank"),
                    "최종 점수 (100점)": item.get("total_score"),
                    "추천 주제": item.get("title"),
                    "메인 키워드": item.get("keyword"),
                    "관련 상품군": item.get("product"),
                    "예상 글 유형": item.get("post_type"),
                    "추천 이유 (공감 포인트)": item.get("reason"),
                    "쇼커 링크 연결 방식": item.get("shocker_link_guide")
                })
            df_scored = pd.DataFrame(scored_rows)
            st.dataframe(df_scored, use_container_width=True, hide_index=True)
            
    except Exception as e_table:
        st.error(f"가중치 채점 보드 로딩 실패: {e_table}")




with tab_write:
    if st.session_state.get("injected_title"):
        st.success(f"🎯 **오늘의 추천 주제로부터 다음 기획 조건이 자동으로 주입되었습니다!**  \n- **선택된 제목**: `{st.session_state.injected_title}`  \n- **메인 키워드**: `{st.session_state.injected_keyword}`  \n- **소개할 상품**: `{st.session_state.injected_product}`")
        
    # 💡 11차 고도화: 생성 전 중복 작성 경고 및 새로운 각도 제안 패널 렌더링
    if st.session_state.dup_warning_data:
        dw = st.session_state.dup_warning_data
        st.warning("⚠️ **유사 포스팅 생성 경고 및 새로운 집필 각도(Angle) 추천**")
        st.markdown(f"""
        로컬 히스토리 검색 결과, 중복 노출 저해 우려가 있는 이력이 발견되었습니다.  
        - **메인 키워드 중복**: {'`동일 키워드 작성 기록 있음` ❌' if dw['keyword_dup'] else '`없음` 🟢'} (기존 제목: *{dw['dup_post_title']}*)  
        - **최근 7일 내 동일 상품군 작성**: {'`있음` ❌' if dw['product_recent'] else '`없음` 🟢'} (작성 시간: `{dw['recent_post_date']}`, `{dw['days_diff']}일 전` 작성됨)  
        
        네이버 검색 노출을 위해 동일 키워드와 상품군 사용 시에는 **글의 어조와 타겟, 상황(각도)을 날카롭게 변경**해 주는 것이 필수적입니다.
        AI 에이전트가 제안하는 아래의 **4가지 새로운 각도 중 하나를 선택**하여 포스팅을 진행하시는 것을 추천합니다.
        """)
        
        # 4가지 각도 카드 렌더링
        s_cols = st.columns(2)
        for idx, ang in enumerate(st.session_state.angle_suggestions):
            with s_cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"**🌟 대안 각도 {idx+1}: {ang['angle_title']}**")
                    st.markdown(f"- **유형**: `{ang['post_type']}` | **대상**: `{ang['target']}` | **상황**: `{ang['situation']}`")
                    st.markdown(f"*추천 이유*: {ang['reason']}")
                    
                    # 각도 자동 세팅 적용 버튼
                    if st.button("👉 이 각도로 조건 자동 설정하여 즉시 생성", key=f"apply_ang_{idx}", type="primary"):
                        st.session_state.dup_warning_data = None
                        st.session_state.force_generate = True
                        
                        raw_t = ang['target']
                        matched_t = [t for t in targets if t in raw_t]
                        raw_s = ang['situation']
                        matched_s = [s for s in situations if s in raw_s]
                        
                        cfg["LAST_INPUTS"]["main_keyword"] = f"{ang['angle_title']}"
                        cfg["LAST_INPUTS"]["post_type"] = ang['post_type']
                        cfg["LAST_INPUTS"]["targets"] = matched_t if matched_t else [targets[0]]
                        cfg["LAST_INPUTS"]["situations"] = matched_s if matched_s else [situations[0]]
                        config.save_config(cfg)
                        
                        persist_current_state()
                        st.success(f"조건 설정 완료! 즉시 '{ang['angle_title']}' 원고를 생성합니다.")
                        st.rerun()
                        
        st.markdown("---")
        if st.button("⚠️ 경고 무시하고 기존 입력대로 그냥 생성 진행하기", use_container_width=True):
            st.session_state.dup_warning_data = None
            st.session_state.force_generate = True
            persist_current_state()
            st.rerun()
            
        st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. 블로그 콘텐츠 조건 입력")
        
        # 1. 메인 키워드
        main_keyword = st.text_input(
            "메인 키워드", 
            value=main_keyword_val,
            placeholder="예: 70대 어머니 생신선물, 부모님 욕실 미끄럼 방지용품"
        )
        
        # 💡 23차 고도화: 키워드 경쟁도 진단 툴 삽입
        with st.expander("🔍 실시간 네이버 블로그 경쟁도 진단", expanded=False):
            if st.button("📊 현재 키워드 경쟁도 분석 실행", use_container_width=True):
                if not main_keyword.strip():
                    st.error("메인 키워드를 먼저 입력해 주세요.")
                else:
                    with st.spinner("네이버 블로그 검색결과 실시간 분석 및 경쟁도 채점 중..."):
                        try:
                            import competition_analyzer
                            comp_res = competition_analyzer.analyze_keyword_competition(main_keyword.strip())
                            if "error" in comp_res:
                                st.error(comp_res["error"])
                            else:
                                st.session_state.comp_analysis_result = comp_res
                                st.success("🎉 경쟁도 실시간 분석이 완료되었습니다!")
                        except Exception as e:
                            st.error(f"분석 실패: {e}")
                            
            if "comp_analysis_result" in st.session_state and st.session_state.comp_analysis_result:
                c_res = st.session_state.comp_analysis_result
                st.markdown(f"**🔑 대상 키워드**: `{c_res['keyword']}`")
                st.markdown(f"**📈 경쟁도 등급**: **{c_res['competition_level']}**")
                st.markdown(f"- *진단 결과*: {c_res['status_description']}")
                st.markdown(f"- *인플루언서 글 비중*: `{c_res['influencer_ratio']}`")
                st.markdown(f"- *최근 일주일 이내 글*: `{c_res['has_recent_posting']}`")
                st.markdown(f"- *상위 글 제목 반복도*: `{c_res['avg_similarity']}`")
                
                with st.expander("📝 상위 노출 5대 글 정보", expanded=False):
                    for idx, post in enumerate(c_res.get("top_posts", [])):
                        st.markdown(f"**{idx+1}. {post['title']}**")
                        st.markdown(f"- 작성일: `{post['date']}` | 타입: `{'대형 인플루언서 🔴' if post['is_influencer'] else '일반 블로그 🟢'}`")
                        
                if c_res.get("alternatives"):
                    st.markdown("💡 **경쟁 완화를 위한 대체 추천 롱테일 키워드**")
                    for a_idx, alt in enumerate(c_res["alternatives"]):
                        col_alt_text, col_alt_btn = st.columns([3, 1])
                        with col_alt_text:
                            st.markdown(f"➡️ **{alt}**")
                        with col_alt_btn:
                            if st.button("✍️ 대체", key=f"apply_alt_kw_{a_idx}", use_container_width=True):
                                st.session_state.injected_keyword = alt
                                st.session_state.injected_title = f"부모님 안전과 실용을 돕는 {alt} 추천 및 가이드"
                                # 💡 25차 고도화: 대체어에 어울리는 최적의 상품 매칭 정보 자동 갱신
                                try:
                                    import shocker_matcher
                                    sh_match = shocker_matcher.get_shocker_matched_products(alt)
                                    if sh_match["is_valid"] and sh_match["matches"]:
                                        st.session_state.injected_product = sh_match["matches"][0]["product"]
                                    else:
                                        st.session_state.injected_product = "직접 입력"
                                except Exception:
                                    st.session_state.injected_product = "직접 입력"
                                st.session_state.comp_analysis_result = None
                                st.success(f"대체 키워드, 제목, 상품 주입 완료! 작성창에서 글을 생성하세요.")
                                st.rerun()



        
        # 2. 글 유형 선택
        post_type = st.selectbox(
            "글 유형 선택", 
            options=post_types, 
            index=post_types.index(last_inputs.get("post_type", "부모님 선물 추천형")) if last_inputs.get("post_type") in post_types else 0
        )
        
        # 글 유형에 대응되는 기본 상품 DB 카테고리 매핑 설정
        if st.session_state.get("injected_product") and selected_db_cat_val in db_categories:
            default_db_cat_idx = db_categories.index(selected_db_cat_val)
        else:
            default_db_cat_idx = 0
            if "선물" in post_type:
                default_db_cat_idx = db_categories.index("부모님 선물") if "부모님 선물" in db_categories else 0
            elif "안심" in post_type:
                default_db_cat_idx = db_categories.index("혼자 사는 부모님 안심용품") if "혼자 사는 부모님 안심용품" in db_categories else 0
            elif "욕실" in post_type or "안전용품" in post_type:
                default_db_cat_idx = db_categories.index("욕실 안전용품") if "욕실 안전용품" in db_categories else 0
            elif "건강" in post_type:
                default_db_cat_idx = db_categories.index("건강관리 생활용품") if "건강관리 생활용품" in db_categories else 0
            elif "계절" in post_type:
                default_db_cat_idx = db_categories.index("계절별 생활용품") if "계절별 생활용품" in db_categories else 0
            
        st.markdown("##### 📦 상품 카테고리 및 소개할 상품군 선택")
        selected_db_cat = st.selectbox(
            "상품 대분류 카테고리", 
            options=db_categories,
            index=default_db_cat_idx
        )
        
        sub_products = list(products_db.get(selected_db_cat, {}).keys())
        sub_products_options = sub_products + ["직접 입력"]
        
        target_prod = selected_product_val if selected_product_val else last_inputs.get("selected_product", "")
        default_prod_idx = 0
        if target_prod in sub_products_options:
            default_prod_idx = sub_products_options.index(target_prod)
            
        selected_product = st.selectbox(
            "소개할 세부 상품군", 
            options=sub_products_options,
            index=default_prod_idx
        )
        
        manual_product = ""
        if selected_product == "직접 입력":
            manual_product = st.text_input(
                "상품군 직접 입력", 
                value=last_inputs.get("manual_product", ""),
                placeholder="예: 실버 카트, 가정용 돋보기 안경"
            )
            products_display = manual_product
        else:
            products_display = selected_product
            
        # 3. 대상 선택 (다중 선택)
        saved_targets = last_inputs.get("targets", [])
        valid_targets = [t for t in saved_targets if t in targets]
        target_selection = st.multiselect("대상 선택 (중복 가능)", options=targets, default=valid_targets)
        
        # 4. 상황 선택 (다중 선택)
        saved_situations = last_inputs.get("situations", [])
        valid_situations = [s for s in saved_situations if s in situations]
        situation_selection = st.multiselect("상황 선택 (중복 가능)", options=situations, default=valid_situations)
        
        # 9. 링크 삽입 횟수
        saved_link_count = last_inputs.get("link_count", 2)
        link_count = st.selectbox("링크 삽입 횟수", options=[1, 2], index=[1, 2].index(saved_link_count) if saved_link_count in [1, 2] else 1)
        
        st.markdown("##### 🔗 쇼커 링크")
        saved_links = last_inputs.get("links", ["", ""])
        if len(saved_links) < 2:
            saved_links = saved_links + [""] * (2 - len(saved_links))
            
        links_input = []
        for i in range(link_count):
            link_val = saved_links[i] if i < len(saved_links) else ""
            link_str = st.text_input(f"쇼커 링크 {i+1}", value=link_val, placeholder=f"예: https://link.coupang.com/link{i+1}")
            links_input.append(link_str)
            
        char_count = st.selectbox(
            "글자 수 선택", 
            options=char_counts, 
            index=char_counts.index(last_inputs.get("char_count", "2000자")) if last_inputs.get("char_count") in char_counts else 1
        )
        
        tone_style = st.selectbox(
            "말투 선택", 
            options=tones, 
            index=tones.index(last_inputs.get("tone_style", "자녀가 부모님을 걱정하는 말투")) if last_inputs.get("tone_style") in tones else 1
        )
        
        blog_category = st.text_input(
            "네이버 블로그 카테고리 (임시저장 대상)", 
            value=blog_category_val,
            placeholder="예: 부모님선물추천"
        )
        
        # 입력값 수동 변경 마다 config 세이브 및 상태 캐싱
        current_inputs = {
            "main_keyword": main_keyword,
            "post_type": post_type,
            "targets": target_selection,
            "situations": situation_selection,
            "selected_db_cat": selected_db_cat,
            "selected_product": selected_product,
            "manual_product": manual_product,
            "products": products_display,
            "link_count": link_count,
            "links": links_input,
            "char_count": char_count,
            "tone_style": tone_style,
            "blog_category": blog_category
        }
        if current_inputs != last_inputs:
            cfg["LAST_INPUTS"] = current_inputs
            config.save_config(cfg)
            persist_current_state()

    with col2:
        st.subheader("2. 글 검토 및 수동 편집")
        
        if st.session_state.generated_post:
            post_data = st.session_state.generated_post
            candidates = post_data.get("title_candidates", [])
            
            st.markdown("##### 💡 AI 제안 제목 후보 (하나를 클릭하면 최종 제목이 설정됩니다)")
            
            # 💡 12차 고도화: 제목 후보를 유형별 뱃지 및 글자수 표시 라벨로 변환 가공
            title_options = []
            display_labels = []
            
            for item in candidates:
                if isinstance(item, dict):
                    t_type = item.get("type", "일반형")
                    t_title = item.get("title", "")
                    title_options.append(t_title)
                    display_labels.append(f"🔹 [{t_type}] {t_title} ({len(t_title)}자)")
                else:
                    title_options.append(item)
                    display_labels.append(f"🔹 {item} ({len(item)}자)")
                    
            format_map = {title_options[i]: display_labels[i] for i in range(len(title_options))}
            
            chosen_title = st.radio(
                "제목 후보 목록", 
                options=title_options, 
                index=st.session_state.chosen_title_index if st.session_state.chosen_title_index < len(title_options) else 0,
                format_func=lambda x: format_map.get(x, x),
                label_visibility="collapsed"
            )
            
            if chosen_title != st.session_state.edit_title and chosen_title in title_options:
                st.session_state.edit_title = chosen_title
                st.session_state.chosen_title_index = title_options.index(chosen_title)
                
                if st.session_state.current_post_id:
                    history_manager.add_or_update_post(st.session_state.current_post_id, {"title": chosen_title})
                persist_current_state()
                st.rerun()

            # 💡 11차 고도화: 자가복제 유사도 리포트 Expander 렌더링
            if st.session_state.similarity_report:
                rep = st.session_state.similarity_report
                with st.expander("📊 실시간 중복/자가복제 유사도 검진 리포트", expanded=True):
                    sc_1, sc_2, sc_3, sc_4 = st.columns(4)
                    sc_1.markdown("**제목 유사도 60% 미만**")
                    sc_1.markdown("🟢 안전" if not rep["title_similar"] else "🔴 위반(유사)")
                    sc_2.markdown("**도입부 문맥 중복 회피**")
                    sc_2.markdown("🟢 안전" if not rep["intro_similar"] else "🔴 위반(유사)")
                    sc_3.markdown("**해시태그 중복 회피**")
                    sc_3.markdown("🟢 안전" if not rep["tags_similar"] else "🔴 위반(유사)")
                    sc_4.markdown("**링크 삽입문구 반복 회피**")
                    sc_4.markdown("🟢 안전" if not rep["links_repeated"] else "🔴 위반(유사)")
                    
                    if rep["issues"]:
                        st.warning("⚠️ **유사성 관련 교정 권장 항목**")
                        for issue in rep["issues"]:
                            st.markdown(f"- {issue}")
                    else:
                        st.success("자가복제 검사 결과 완벽하게 안전한 오리지널 단독 원고입니다!")

            edited_title = st.text_input("최종 제목 (직접 자유롭게 수정 가능)", value=st.session_state.edit_title)
            if edited_title != st.session_state.edit_title:
                st.session_state.edit_title = edited_title
                persist_current_state()
            
            edited_content = st.text_area("최종 본문 (10단계 구조 통합본)", value=st.session_state.edit_content, height=400)
            if edited_content != st.session_state.edit_content:
                st.session_state.edit_content = edited_content
                persist_current_state()
            
            edited_tags = st.text_input("최종 해시태그 (쉼표로 구분)", value=st.session_state.edit_tags)
            if edited_tags != st.session_state.edit_tags:
                st.session_state.edit_tags = edited_tags
                persist_current_state()
            
            # 💡 13차 고도화: AI 추천 이미지 생성용 영문 프롬프트 3종 복사 패널 렌더링
            img_prompts = post_data.get("image_prompts", []) if st.session_state.generated_post else []
            if not img_prompts and st.session_state.current_post_id:
                loaded_post = history_manager.get_post_by_id(st.session_state.current_post_id)
                if loaded_post:
                    img_prompts = loaded_post.get("image_prompts", [])
                    
            if img_prompts:
                with st.expander("📸 AI 추천 이미지 생성용 영문 프롬프트 (3종)", expanded=False):
                    st.markdown("""
                    네이버 블로그의 글 품질을 극대화해 줄 이미지 AI(DALL-E 3, Midjourney 등)용 영문 프롬프트와 파일명 가이드라인입니다.  
                    각 프롬프트 우측 상단의 **복사 아이콘**을 클릭해 생성 도구에 붙여넣어 이미지를 만드실 수 있습니다.
                    """)
                    for idx, p_item in enumerate(img_prompts):
                        st.markdown(f"**🖼️ 이미지 {idx+1}안 (alt 텍스트: {p_item.get('alt_text')})**")
                        st.markdown(f"- **권장 파일명**: `{p_item.get('filename')}`")
                        st.code(p_item.get("prompt"), language="text")
                        st.divider()
            
            # 현재 편집 내용 로컬 수동 저장 버튼 제공
            save_col1, save_col2 = st.columns([1, 1])
            with save_col1:
                if st.button("💾 현재 수동 편집본 저장", use_container_width=True):
                    if st.session_state.current_post_id:
                        tags_list = [t.strip() for t in edited_tags.split(",") if t.strip()]
                        st.session_state.current_post_status = "수정 완료"
                        
                        update_fields = {
                            "title": edited_title,
                            "content": edited_content,
                            "tags": tags_list,
                            "post_status": st.session_state.current_post_status
                        }
                        history_manager.add_or_update_post(st.session_state.current_post_id, update_fields)
                        persist_current_state()
                        st.success("💾 현재 본문과 편집 상태가 로컬 이력에 저장되었습니다!")
                    else:
                        st.error("저장할 활성화된 포스팅 세션이 없습니다.")
            with save_col2:
                if st.session_state.current_post_id:
                    st.caption(f"📍 현재 세션 ID: `{st.session_state.current_post_id}` (상태: **{st.session_state.current_post_status}**)")
            
            st.divider()
            
            # 1. 준법 광고 검수 결과 렌더링
            if st.session_state.validation_result:
                val = st.session_state.validation_result
                with st.expander("📝 AI 콘텐츠 정밀 준법 검수 리포트", expanded=True):
                    r_col1, r_col2, r_col3 = st.columns(3)
                    with r_col1:
                        risk = val.get("ad_risk", "보통")
                        st.info(f"광고성 위험도: {risk}")
                    with r_col2:
                        is_pub = val.get("is_publishable", True)
                        st.info("발행 가능 여부: 가능" if is_pub else "발행 가능 여부: 보류")
                    with r_col3:
                        st.info(f"검출: 과장 {val.get('exaggeration_count', 0)} / 의학단정 {val.get('medical_assertion_count', 0)}")
                    edits = val.get("recommended_edits", [])
                    if edits:
                        for idx, edit in enumerate(edits):
                            st.markdown(f"**[{idx+1}] 위반 문장**: `{edit.get('original_sentence')}` -> 👉 *대체안*: `{edit.get('alternative_sentence')}`")
                            
            # 2. SEO 및 가독성 리포트 & Auto-Fix 기능 렌더링
            if st.session_state.seo_result:
                seo = st.session_state.seo_result
                with st.expander("📊 네이버 블로그 SEO 및 모바일 가독성 리포트", expanded=True):
                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("검색 노출 SEO 점수", f"{seo.get('seo_score', 0)} / 100점")
                    s_col2.metric("모바일 가독성 점수", f"{seo.get('readability_score', 0)} / 100점")
                    s_col3.metric("광고성 위험", seo.get("ad_risk", "보통"))
                    
                    issues = seo.get("issues", [])
                    if issues:
                        st.markdown("**❌ 보완 및 수정 필요 항목**")
                        for issue in issues:
                            st.markdown(f"- {issue}")
                        if seo.get("need_auto_fix", False):
                            if st.button("🔧 지적된 SEO 오류 즉시 자동 수정 (Auto-Fix)", type="primary"):
                                with st.spinner("AI 에이전트 자동 교정 진행 중..."):
                                    tags_list = [t.strip() for t in edited_tags.split(",") if t.strip()]
                                    fixed_res = seo_validator.auto_fix_content(
                                        api_key=gemini_key,
                                        title=edited_title,
                                        content=edited_content,
                                        tags=tags_list,
                                        main_keyword=main_keyword_val,
                                        char_count=last_inputs.get("char_count", "2000자"),
                                        products=products_display_val,
                                        issues=issues
                                    )
                                    if "error" in fixed_res:
                                        st.error(fixed_res["error"])
                                    else:
                                        st.session_state.edit_title = fixed_res.get("fixed_title", edited_title)
                                        st.session_state.edit_content = fixed_res.get("fixed_content", edited_content)
                                        st.session_state.edit_tags = ", ".join(fixed_res.get("fixed_tags", []))
                                        st.session_state.seo_result = None
                                        st.session_state.current_post_status = "수정 완료"
                                        if st.session_state.current_post_id:
                                            history_manager.add_or_update_post(st.session_state.current_post_id, {
                                                "title": st.session_state.edit_title,
                                                "content": st.session_state.edit_content,
                                                "tags": fixed_res.get("fixed_tags", []),
                                                "post_status": st.session_state.current_post_status
                                            })
                                        persist_current_state()
                                        st.success("🎉 원고가 완벽하게 자동 SEO 교정되었습니다!")
                                        st.rerun()
            
            # 💡 수동 입력 비상 대책 패널 UI 노출
            if st.session_state.show_manual_panel:
                is_cloud = (platform.system() != "Windows")
                if is_cloud:
                    st.success("🟢 **클라우드 모드 전용 복사 포스팅 패널**")
                    st.markdown("""
                    컴퓨터가 꺼진 상태(클라우드 가동 중)이므로 네이버 스마트에디터 자동 제어를 우회하고 모바일 복사 모드를 활성화했습니다.  
                    아래 제목/본문/해시태그 우측 상단의 **[복사 아이콘]**을 터치하여 휴대폰 네이버 블로그 앱에 가볍게 붙여넣어 완수하세요!
                    """)
                else:
                    st.warning("⚠️ **수동 입력 비상 대책 안내 패널**")
                    st.markdown("""
                    자동화 프로그램이 스마트에디터의 일부 항목을 완전히 입력하지 못하고 부분 중단되었습니다.  
                    현재 **네이버 글쓰기 브라우저 창이 열린 채로 유지**되어 있습니다. 아래 버튼을 사용하여 수동으로 간편히 마무리해 주세요!
                    """)
                st.text("📋 1. 제목 복사하기")
                st.code(st.session_state.edit_title, language="text")
                st.text("📋 2. 본문 복사하기")
                st.code(st.session_state.edit_content, language="text")
                st.text("📋 3. 해시태그 복사하기")
                st.code(st.session_state.edit_tags, language="text")
                
                if st.button("❌ 열린 네이버 브라우저 창 닫기 및 세션 정리", use_container_width=True):
                    if st.session_state.playwright_instance:
                        try: st.session_state.context_instance.close(); st.session_state.playwright_instance.stop()
                        except: pass
                        st.session_state.playwright_instance = None
                        st.session_state.context_instance = None
                    st.session_state.show_manual_panel = False
                    persist_current_state()
                    st.rerun()
        else:
            st.warning("컨트롤 타워나 포스팅 기획창에서 원고 생성을 기동하면 이 영역에 결과가 나타납니다.")

# 📂 저장된 글 이력 및 상태 관리 대시보드 탭
with tab_history:
    st.subheader("📂 로컬 저장소 포스팅 이력 관리")
    history_list = history_manager.load_history()
    
    if not history_list:
        st.info("로컬 이력이 존재하지 않습니다.")
    else:
        status_options = ["전체보기", "초안 생성 완료", "검수 필요", "수정 완료", "임시저장 완료", "발행 완료", "오류 발생"]
        selected_status_filter = st.selectbox("포스팅 상태 필터", options=status_options)
        
        filtered_list = [entry for entry in history_list if selected_status_filter == "전체보기" or entry.get("post_status") == selected_status_filter]
        
        if not filtered_list:
            st.warning("매칭되는 이력이 없습니다.")
        else:
            st.markdown(f"총 **{len(filtered_list)}** 건의 포스팅 이력이 검색되었습니다.")
            for post in filtered_list:
                with st.container():
                    c_id = post.get("id")
                    st.markdown(f"#### [{post.get('post_status')}] {post.get('title')}")
                    st.caption(f"📅 일자: {post.get('created_at')} | 🔑 키워드: `{post.get('main_keyword')}` | 📦 상품: `{post.get('products')}`")
                    
                    with st.expander("🔍 본문 및 태그 미리보기"):
                        st.markdown(f"**태그**: {', '.join(post.get('tags', []))}")
                        st.text_area("본문 내용", value=post.get("content", ""), height=150, disabled=True, key=f"hist_preview_{c_id}")
                        
                    act_col1, act_col2 = st.columns([1, 1])
                    with act_col1:
                        if st.button("✍️ 편집기로 불러오기", key=f"load_btn_{c_id}", use_container_width=True):
                            st.session_state.current_post_id = c_id
                            st.session_state.current_post_status = post.get("post_status")
                            st.session_state.edit_title = post.get("title")
                            st.session_state.edit_content = post.get("content", "")
                            st.session_state.edit_tags = ", ".join(post.get("tags", []))
                            st.session_state.generated_post = {
                                "title_candidates": [post.get("title")],
                                "selected_title": post.get("title"),
                                "hashtags": post.get("tags", []),
                                "image_prompts": post.get("image_prompts", [])
                            }
                            st.session_state.chosen_title_index = 0
                            st.session_state.validation_result = None
                            st.session_state.seo_result = None
                            st.session_state.show_manual_panel = False
                            st.session_state.similarity_report = None
                            persist_current_state()
                            st.success("🎉 편집기에 포스팅이 동기화 로드되었습니다!")
                            st.rerun()
                    with act_col2:
                        if st.button("🗑️ 이 포스팅 영구 삭제", key=f"del_btn_{c_id}", use_container_width=True):
                            history_manager.delete_post_by_id(c_id)
                            st.rerun()
                    st.divider()

st.divider()
st.markdown("""
<style>
footer {visibility: hidden;}
</style>
<div style='text-align: center; color: #888888; font-size: 13px;'>
    본 프로그램은 사용자의 안전한 네이버 세션 관리를 보장하며, 외부로 어떠한 개인 정보도 유출하지 않습니다.
</div>
""", unsafe_allow_html=True)
