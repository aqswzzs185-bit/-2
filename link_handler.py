import random

# 다채로운 링크 자연어 템플릿 정의 (직접 광고 유도 배제, 시니어 정보 가이드에 포커싱)
LINK_PREFIX_TEMPLATES = [
    "부모님 댁 주거 여건이나 욕실 구조에 잘 맞는지 아래 상세 사양을 먼저 대조해 보시는 것을 권해드립니다.",
    "실제 고령자 분들이 사용하실 때 안전 규격(KC 인증 등)을 통과했는지 상세 정보를 한 번 더 확인해 보세요.",
    "무게가 너무 무겁지는 않은지, 부모님이 쥐기에 그립감이 편한지 아래에서 실측 치수를 확인하시는 것이 좋습니다.",
    "이 제품군의 상세한 작동 방식과 직관적인 버튼 구성을 미리 체크하고 결정하시는 것이 안전합니다.",
    "자녀분들이 매번 방문해서 챙겨드리기 어려울 때 요긴한 실용적 모델의 상세 조건은 다음과 같습니다.",
    "부모님 관절 상태나 거동 정도에 따라 알맞은 모델 규격이 다를 수 있으니 아래에서 먼저 대조해 보세요.",
    "시기에 따라 가격대와 패키지 구성 혜택이 상이할 수 있으니 아래 페이지를 통해 꼼꼼하게 알아두는 것이 현명합니다.",
    "많은 자녀분들이 부모님 안심용으로 주로 선택하는 대표적인 사양과 비교 정보는 아래에서 참고 가능합니다."
]

LINK_SUFFIX_TEMPLATES = [
    "세부 기능과 실제 사용자분들의 사용 팁은 아래 남겨드린 상세 내역에서 좀 더 명확하게 확인하실 수 있습니다.",
    "부모님의 더 안전하고 편안한 하루를 위한 유용한 세부 정보는 아래에서 조용히 참고해 보시기 바랍니다.",
    "어디서부터 챙겨드려야 할지 고민되신다면 아래 상세 모델 안내를 활용해 가볍게 힌트를 얻어보세요.",
    "부모님 생활 동선을 한결 편안하게 업그레이드해 줄 안심 장치의 상세한 모델 정보는 아래 링크에서 안내받으실 수 있습니다.",
    "직접 사용해 보신 분들의 진솔한 평판과 제품의 구체적인 무게, 크기 정보는 아래에서 확인해 보세요."
]

def generate_natural_link_paragraph(product_name: str, link_url: str, db_link_text: str = "") -> str:
    """
    상품명과 링크 URL, DB 권장 문구를 조화롭게 버무려 직접 구매를 유도하지 않는
    따뜻하고 자연스러운 링크 삽입 문단을 생성합니다.
    """
    if not link_url or not link_url.strip():
        return ""
    
    # 1. 문장 구성 패턴 결정
    prefix = random.choice(LINK_PREFIX_TEMPLATES)
    suffix = random.choice(LINK_SUFFIX_TEMPLATES)
    
    # 2. DB에 특화된 링크 문구가 존재하면 확률적으로 절반 이상 섞어서 적용하여 맞춤도를 높임
    if db_link_text and db_link_text.strip() and random.random() > 0.3:
        # DB 문장이 자연스럽게 녹아나도록 설정
        core_msg = db_link_text.strip()
        paragraph = f"{prefix}\n{core_msg}\n👉 {link_url.strip()}\n{suffix}"
    else:
        paragraph = f"{prefix}\n부모님 일상에 도움이 될 만한 {product_name} 제품의 상세 구조와 세부 요건을 꼼꼼하게 따져보시는 것이 도움이 됩니다.\n👉 {link_url.strip()}\n{suffix}"
        
    return paragraph

def assemble_post_with_links(post_data: dict, links: list, link_count: int, product_name: str, db_link_text: str = "") -> str:
    """
    AI가 작성한 원고 10단계 구성 요소를 조합하되,
    사용자가 선택한 링크 삽입 횟수(1회 또는 2회) 및 위치 규칙을 엄격하게 지켜
    최종 하나의 마크다운/텍스트 본문으로 조립합니다.
    
    규칙:
    - 도입부에는 절대 링크를 넣지 않음.
    - 첫 번째 링크: 본문 중간 (소제목 & 본문 섹션들 중 2~3번째 섹션 직후)에 배치.
    - 두 번째 링크: 사용자 선택이 2회이고 링크가 2개 입력되었을 때, 마무리(conclusion) 문단 바로 직전에 배치.
    - 링크 전후로는 빈 줄을 크게 두어 모바일 가독성 확보.
    """
    content_parts = []
    
    # 1. 도입부 추가 (링크 없음)
    if post_data.get("introduction"):
        content_parts.append(post_data["introduction"])
        
    # 2. 소제목 & 본문 섹션들 결합
    subtitles = post_data.get("subtitles", [])
    body_sections = post_data.get("body_sections", [])
    
    # 유효한 링크 추출
    valid_links = [l.strip() for l in links if l and l.strip()]
    
    # 링크 단락 생성
    link_para_1 = ""
    link_para_2 = ""
    
    if len(valid_links) >= 1:
        link_para_1 = generate_natural_link_paragraph(product_name, valid_links[0], db_link_text)
    if len(valid_links) >= 2 and link_count == 2:
        link_para_2 = generate_natural_link_paragraph(product_name, valid_links[1], db_link_text)
        
    # 본문 중간 삽입 위치 결정 (보통 섹션이 4개 이상이면 2번째 섹션 뒤에 꽂음)
    insert_idx = min(2, len(body_sections))
    
    for idx, (sub, body) in enumerate(zip(subtitles, body_sections)):
        content_parts.append(f"■ {sub}\n{body}")
        
        # 중간 삽입 조건 충족 시 첫 번째 링크 문단 꽂아넣기
        if idx + 1 == insert_idx and link_para_1:
            content_parts.append(link_para_1)
            
    # 3. 만약 섹션 수가 너무 적어 중간 링크가 누락되었거나 링크 카운트 대비 못 들어간 경우 방지
    # (예컨대 바디 섹션이 아예 없었을 경우)
    if link_para_1 and link_para_1 not in content_parts:
        content_parts.append(link_para_1)
        
    # 4. 선택 기준 정리 추가
    if post_data.get("selection_criteria"):
        content_parts.append(f"📌 [선택 기준 정리]\n{post_data['selection_criteria']}")
        
    # 5. 주의사항 추가
    if post_data.get("precautions"):
        content_parts.append(f"⚠️ [사용 시 주의사항]\n{post_data['precautions']}")
        
    # 6. 두 번째 링크 추가 (2회 삽입 조건 충족 시 마무리 바로 직전)
    if link_count == 2 and link_para_2:
        content_parts.append(link_para_2)
        
    # 7. 마무리 추가
    if post_data.get("conclusion"):
        content_parts.append(post_data["conclusion"])
        
    # 각 파트를 두 줄 개행(\n\n)으로 결합하여 넓은 모바일 가독성 레이아웃 확보
    assembled_content = "\n\n".join(content_parts)
    
    return assembled_content
