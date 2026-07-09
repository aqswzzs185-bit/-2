import google.generativeai as genai
import json
import re
from datetime import datetime

def get_jaccard_similarity(str1: str, str2: str, by_char: bool = True) -> float:
    """
    두 문자열 간의 자카드 유사도(Jaccard Similarity)를 계산합니다.
    by_char가 True이면 음절(글자) 단위로, False이면 어절(단어) 단위로 쪼개어 연산합니다.
    """
    s1 = re.sub(r"\s+", "", str1) if by_char else str1.split()
    s2 = re.sub(r"\s+", "", str2) if by_char else str2.split()
    
    set1 = set(s1)
    set2 = set(s2)
    
    if not set1 or not set2:
        return 0.0
        
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    
    return len(intersection) / len(union)

def check_duplication_before_generation(history: list, main_keyword: str, product: str) -> dict:
    """
    초안 생성 전, 동일 메인 키워드 중복 작성 여부 및 
    동일 상품군의 최근 7일 내 집필 기록 여부를 확인합니다.
    """
    keyword_dup = False
    product_recent = False
    dup_post_title = ""
    recent_post_date = ""
    days_diff = 999
    
    now = datetime.now()
    
    for post in history:
        # 1. 키워드 중복 검사
        if post.get("main_keyword", "").strip().lower() == main_keyword.strip().lower():
            keyword_dup = True
            dup_post_title = post.get("title", "")
            
        # 2. 최근 7일 내 동일 상품군 검사
        if post.get("products", "").strip().lower() == product.strip().lower():
            created_at_str = post.get("created_at")
            if created_at_str:
                try:
                    created_date = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                    diff = (now - created_date).days
                    if diff < 7:
                        product_recent = True
                        if diff < days_diff:
                            days_diff = diff
                            recent_post_date = created_at_str
                except Exception as date_e:
                    print(f"[Similarity] 날짜 파싱 에러: {date_e}")
                    
    return {
        "keyword_dup": keyword_dup,
        "dup_post_title": dup_post_title,
        "product_recent": product_recent,
        "recent_post_date": recent_post_date,
        "days_diff": days_diff
    }

def check_generated_content_similarity(history: list, title: str, content: str, tags: list) -> dict:
    """
    초안 생성 완료 후, 제목의 60% 이상 유사 여부, 도입부 유사성, 
    해시태그 중복성, 쇼커 링크 안내 문구의 중복 사용 여부를 점검합니다.
    """
    issues = []
    title_similar = False
    intro_similar = False
    tags_similar = False
    links_repeated = False
    
    # 생성된 글의 도입부 섹션 추출 (대체로 첫 250글자 또는 개행 첫 두 문단)
    intro_paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
    generated_intro = " ".join(intro_paragraphs[:2]) if intro_paragraphs else ""
    
    # 생성된 글의 링크 삽입 문구들 추출 (👉 https:// 형태로 이어진 줄의 텍스트)
    generated_link_lines = [line.strip() for line in content.split("\n") if "👉" in line]
    
    for post in history:
        # 1. 제목 유사도 점검 (음절 자카드 유사도가 60% 이상인 경우 감지)
        t_sim = get_jaccard_similarity(post.get("title", ""), title, by_char=True)
        if t_sim >= 0.6:
            title_similar = True
            issues.append(f"기존 포스팅 [{post.get('title')}]과 제목이 약 {int(t_sim * 100)}% 유사합니다. (60% 이상 중복 경보)")
            
        # 2. 도입부 유사도 점검 (음절 유사도가 50% 이상인 경우 감지)
        post_content = post.get("content", "")
        post_paragraphs = [p.strip() for p in post_content.split("\n") if p.strip()]
        post_intro = " ".join(post_paragraphs[:2]) if post_paragraphs else ""
        
        i_sim = get_jaccard_similarity(post_intro, generated_intro, by_char=True)
        if i_sim >= 0.5:
            intro_similar = True
            issues.append(f"기존 원고 도입부와 표현 및 문장이 약 {int(i_sim * 100)}% 겹칩니다. (자가 복제 우려)")
            
        # 3. 해시태그 유사도 점검 (태그셋이 80% 이상 일치하는지)
        post_tags = post.get("tags", [])
        tag_sim = get_jaccard_similarity(", ".join(post_tags), ", ".join(tags), by_char=False) # 단어 기반
        if tag_sim >= 0.8:
            tags_similar = True
            issues.append(f"이전 글과 태그 셋 구성이 {int(tag_sim * 100)}% 일치하여 매번 동일한 해시태그가 반복되고 있습니다.")
            
        # 4. 링크 안내 문구 반복 점검
        post_link_lines = [line.strip() for line in post_content.split("\n") if "👉" in line]
        for g_line in generated_link_lines:
            # 특수기호나 URL을 제외한 순수 텍스트 영역 추출 비교
            g_clean = re.sub(r"https?://[^\s]+", "", g_line).replace("👉", "").strip()
            for p_line in post_link_lines:
                p_clean = re.sub(r"https?://[^\s]+", "", p_line).replace("👉", "").strip()
                if g_clean == p_clean and len(g_clean) > 5:
                    links_repeated = True
                    issues.append(f"쇼커 링크 삽입 문구 '{g_clean}'가 기존 글과 완전히 동일하게 반복되었습니다.")
                    break
            if links_repeated:
                break
                
    return {
        "title_similar": title_similar,
        "intro_similar": intro_similar,
        "tags_similar": tags_similar,
        "links_repeated": links_repeated,
        "issues": list(set(issues)) # 중복 메시지 정리
    }

def suggest_new_angles(api_key: str, main_keyword: str, product: str, existing_titles: list) -> list:
    """
    Gemini API를 호출하여 기존에 쓰인 기획 글들의 어조/소재와 다른
    4가지 창의적인 '새로운 작문 각도(Angle)'를 생성하여 추천합니다.
    """
    if not api_key:
        # 기본 대체 제안 목록 반환
        return [
            {
                "angle_title": f"혼자 사는 부모님을 위한 실용적인 {product}",
                "post_type": "혼자 사는 부모님 안심용품형",
                "target": "혼자 사는 부모님",
                "situation": "혼자 거주",
                "reason": "최근 작성된 선물/안전 정보 글과 겹치지 않게 '독거 안심 예방' 각도를 설정했습니다."
            },
            {
                "angle_title": f"낙상 방지 관점에서 본 {product} 고르는 법",
                "post_type": "욕실·침실·주방 안전용품형",
                "target": "부모님 공통",
                "situation": "욕실 안전",
                "reason": "안전사고 예방의 필요성을 사실적으로 묘사하여 각도를 전환했습니다."
            },
            {
                "angle_title": f"부모님이 겨울철에 쓰기 좋은 안심 {product}",
                "post_type": "계절별 생활용품형",
                "target": "부모님 공통",
                "situation": "겨울",
                "reason": "계절적 특수성(혹한기 안전 대비)을 결합하여 각도를 변환했습니다."
            },
            {
                "angle_title": f"부모님 신체 변화에 따른 {product} 선택 리스트",
                "post_type": "건강관리 생활용품형",
                "target": "60대 / 70대",
                "situation": "건강관리",
                "reason": "건강 검진 및 노인성 질병 관리 차원의 기능성 추천 각도입니다."
            }
        ]
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        titles_str = "\n".join([f"- {t}" for t in existing_titles]) if existing_titles else "없음"
        
        prompt = f"""
당신은 네이버 블로그 콘텐츠 작문 각도 다변화를 조율하는 전문 에디터입니다.
사용자가 입력한 키워드와 상품군은 이미 최근 블로그에 포스팅된 기록이 있어, 자칫하면 중복 문서 판정을 받거나 이웃 독자들이 지루하게 느낄 위험이 있습니다.
기존 포스팅들의 제목 및 기조와는 **완전히 다른 4가지 새로운 작문 각도(Angle)**를 설계해 주세요.

[입력 정보]
- 메인 키워드: {main_keyword}
- 소개 상품군: {product}
- 기존 작성된 제목 목록:
{titles_str}

[교정 각도 제안 방향 예시]
기존 글이 단순한 생신선물 추천("70대 어머니 생신선물 추천")이었다면, 제안 각도는 다음처럼 각도를 날카롭게 꺾어야 합니다:
- '혼자 계신 어머니의 안전을 위한 안심선물 관점' (혼자 사는 부모님 안심용품형)
- '겨울철 한파 대비 체온 관리 관점' (계절별 생활용품형)
- '미끄럼 방지 등 특정 안전 사고 예방 관점' (안전용품형)
- '노화에 따른 신체 불편 관점' (생활문제 해결형)

[출력 규격]
반드시 아래의 JSON 배열 형식으로만 응답하세요. 다른 설명은 생략하십시오.

[
  {{
    "angle_title": "제안하는 신선한 새 제목 방향",
    "post_type": "부모님 선물 추천형 또는 시니어 생활문제 해결형 등 기존 글 유형 중 하나 선택",
    "target": "어머니 또는 아버지 또는 혼자 사는 부모님 등 최적 타겟 선택",
    "situation": "생신 또는 겨울 또는 욕실 안전 또는 혼자 거주 등 최적 상황 1~2개 기입",
    "reason": "이 각도가 기존 포스팅과 비교해 왜 신선한지 설명 (따뜻한 자녀 관점 반영)"
  }}
]
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response_text = response.text.strip()
        
        if response_text.startswith("```json"):
            response_text = re.sub(r"^```json\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
        elif response_text.startswith("```"):
            response_text = re.sub(r"^```\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
            
        data = json.loads(response_text)
        return data
        
    except Exception as e:
        print(f"[Similarity] 각도 추천 에러: {e}")
        # 오류 시 기본값 반환
        return suggest_new_angles("", main_keyword, product, existing_titles)
