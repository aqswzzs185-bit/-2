import os
import json
import re
import urllib.request
import urllib.error

def call_gemini_rest_api(api_key: str, prompt: str, model_name: str = "gemini-1.5-flash") -> str:
    """
    google-generativeai SDK의 404 엔드포인트 충돌을 완벽히 방지하기 위해
    구글 공식 Gemini v1 REST API로 직접 POST 요청을 날려 텍스트 결과를 반환합니다.
    """
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    req_body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            raise Exception("올바른 응답 데이터를 받지 못했습니다.")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_body)
            err_msg = error_json.get("error", {}).get("message", str(e))
        except Exception:
            err_msg = error_body
        raise Exception(f"HTTP {e.code}: {err_msg}")
    except Exception as e:
        raise Exception(str(e))


def generate_blog_post(
    api_key: str, 
    main_keyword: str, 
    post_type: str, 
    targets: list, 
    situations: list, 
    products: str, 
    links: list, 
    char_count: str, 
    tone_style: str, 
    blog_category: str, 
    base_tone_guide: str,
    db_product_info: dict = None
):
    """
    10단계 글 구조를 완벽히 준수하며, 외부 링크를 본문에 직접 오염시키지 않고
    순수한 정보성 파트로 나누어 생성합니다. 최종 링크 조립은 전용 모듈에서 수행됩니다.
    """
    if not api_key:
        return {"error": "Gemini API Key가 설정되지 않았습니다. 설정에서 등록해 주세요."}
    
    try:
        
        targets_str = ", ".join(targets) if targets else "부모님"
        situations_str = ", ".join(situations) if situations else "안전 및 건강 관리"
        
        # 링크 가공
        links_info = ""
        valid_links = [l.strip() for l in links if l and l.strip()]
        for i, val in enumerate(valid_links):
            links_info += f"- 링크 {i+1}: {val}\n"
            
        # 상품군 DB 컨텍스트 조립
        db_context = ""
        if db_product_info:
            db_context = f"""
[상품군 데이터베이스(DB) 참고 지식]
소개하는 상품 '{products}'은 아래의 전문 DB 지식에 근거하여 작성해야 합니다.
- 관련 검색 키워드: {", ".join(db_product_info.get("keywords", []))}
- 적합한 부모님 생활 상황: {db_product_info.get("situations", "")}
- 추천 제목 예시 패턴: {db_product_info.get("title_example", "")}
- 핵심적인 기능/재질 선택 기준: {db_product_info.get("criteria", "")}
- 시니어 안전 사용 시 주의사항: {db_product_info.get("precautions", "")}
- 권장되는 자연스러운 링크 삽입용 문장 뉘앙스: {db_product_info.get("link_text", "")}

*작성 지침*: 
1. 본문의 '선택 기준 정리' 단락에는 DB의 '선택 기준'을 반드시 녹여 넣으세요.
2. 본문의 '주의사항 작성' 단락에는 DB의 '시니어 안전 사용 시 주의사항' 팩트를 정확히 지켜 서술하되, 절대 기계적인 복사-붙여넣기가 아닌 설정된 말투 스타일({tone_style})에 어울리게 가공하여 작성하세요.
3. 쇼커 링크가 들어갈 문단은 DB의 '자연스러운 링크 삽입용 문장 뉘앙스'를 참고하여 자녀의 마음이 느껴지도록 녹여내세요.
"""

        # 글 유형별 구조 템플릿 정의
        post_type_guide = ""
        if post_type == "부모님 선물 추천형":
            post_type_guide = "선물로써의 실용성과 정성, 감사의 가치를 돋보이게 합니다."
        elif post_type == "시니어 생활문제 해결형":
            post_type_guide = "몸이 예전 같지 않아 겪으시는 작은 생활 속 불편함의 원인을 짚고 생활 보조용품을 통한 해결책을 다룹니다."
        elif post_type == "혼자 사는 부모님 안심용품형":
            post_type_guide = "멀리 떨어져 계신 부모님의 욕실, 주방 등 일상 속 안전사고에 대한 자녀의 불안감을 덜어줄 안심 보조용품의 필요성을 다룹니다."
        elif post_type == "계절별 생활용품형":
            post_type_guide = "폭염, 한파, 장마철 등 계절 변화에 따른 체력 저하와 사고 위험 요소를 지적하고 예비 요령을 다룹니다."
        elif post_type == "비교 추천형":
            post_type_guide = "제품의 구체적인 형식별 장단점 비교 기준을 공정하게 분석하여 올바른 구매 방법을 제안합니다."
        else:
            post_type_guide = "부모님의 안전과 편의 향상을 위한 구체적 예방 지침과 가이드를 다룹니다."

        # 어조 설정
        tone_guide = ""
        if tone_style == "따뜻한 정보형":
            tone_guide = "다정하고 따뜻한 어조 (~해요, ~합니다)로 시니어 꿀팁을 전하는 친근한 안내체"
        elif tone_style == "자녀가 부모님을 걱정하는 말투":
            tone_guide = "부모님 댁을 챙기는 자녀의 1인칭 관점. '저희 부모님도...', '바쁘다는 핑계로 자주 가보지 못해 늘 마음에 걸렸는데...' 등의 진정성 가득한 걱정과 정이 깃든 독백형 어조 (~더라고요, ~해드려야겠어요)"
        elif tone_style == "차분한 전문가형":
            tone_guide = "객관적이고 신뢰도 높은 정보성 조언체 (~입니다, ~합니다). 공학적 및 시니어 건강 지식을 알기 쉽게 설명"
        elif tone_style == "블로그 자연체":
            tone_guide = "일상 소통형 블로그 어법 (~네요, ~합니다, ~추천드려요)"
        elif tone_style == "후기형":
            tone_guide = "실제 제품을 직접 설치/선물해 드린 뒤 부모님이 좋아하시던 반응을 가감 없이 담아낸 감동 어린 리뷰체 (~해보니, ~하셨어요, ~더라고요)"

        char_num = re.sub(r"[^0-9]", "", char_count)
        
        prompt = f"""
당신은 네이버 블로그 포스팅 전문 작가이자 부모님 케어 전문 크리에이터입니다.
다음 조건들을 완벽히 만족하여 구조화된 블로그 글을 생성해 주세요.

[콘텐츠 작성 원칙]
1. [구조 및 전개]: 
   - 상품을 바로 팔려고 유도하지 말고, 도입부에서는 독자의 상황과 부모님 걱정에 깊이 공감하는 일상적인 내용으로 시작하세요.
   - 전문적인 척 지식을 나열하기보다는 비전문가(부모님을 둔 보통의 자녀들)가 보아도 한눈에 알기 쉽게 편안한 문장으로 설명하세요.
   - 정보의 객관성을 지키기 위해 과장 광고 표현이나 의학적 치료 효과를 단정 짓는 말은 일절 금지합니다.
   - 특히 “효과 보장”, “완치”, “무조건 필요”, “최고의 효능” 등의 단어는 절대 사용하지 말고, “일상의 완화에 도움을 줍니다”, “안전을 예방하는 데 든든한 보탬이 됩니다” 등으로 부드럽게 쓰세요.
2. [문단 및 가독성 (매우 중요)]:
   - 네이버 블로그 모바일 앱 가독성에 최적화되도록 **한 문단은 2~4문장 이내**로 대단히 짧게 작성하세요.
   - 모바일 화면 가로 폭에 맞추어 문단 사이사이에 엔터(줄바꿈)를 충분히 크게 넣어 시원시원한 레이아웃을 만드세요.
3. [링크 기재 금지]:
   - **중요**: `introduction`, `body_sections`, `selection_criteria`, `precautions`, `conclusion` 등 아래 반환할 본문 텍스트 안에는 어떠한 외부 웹링크 주소(URL, http://...)도 절대 적지 마세요. 외부 링크가 직접 삽입되면 포스팅의 독립성이 손상될 수 있으므로, 오직 100% 순수한 한글 정보성 글자만으로 완성도 있게 채우셔야 합니다.
   - 오직 `shopping_link_paragraph` 필드에만 자연스럽게 링크가 들어갈 문장 뉘앙스의 초안을 1문장 내외로 뱉으시면 됩니다.

{db_context}

[입력 정보]
- 메인 키워드: {main_keyword} (제목과 본문 오프닝, 본문 중간, 마무리 단락에 자연스러운 흐름으로 각각 1회씩 총 3회 이상 언급할 것)
- 글 유형: {post_type} (가이드: {post_type_guide})
- 대상 타겟: {targets_str}
- 상황 배경: {situations_str}
- 소개할 상품군: {products}
- 쇼핑 링크:
{links_info if links_info else "(제공된 링크 없음)"}
- 목표 분량: 최소 {char_num}자 내외
- 말투: {tone_style} (구체적 스타일: {tone_guide})
- 기본 톤앤매너: {base_tone_guide if base_tone_guide else "따뜻하고 정중한 어조"}

[AI 이미지 프롬프트 생성 10대 조건]
블로그 글의 주제 및 소개 상품군({products})에 연동되는 이미지 생성용 영문 프롬프트를 3개 자동 생성해야 합니다.
1. 장면 테마: 부모님이 상품을 사용 중인 일상 / 자녀가 부모님께 선물을 전달하는 장면 / 독거 시니어의 아늑한 일상 생활
2. 타겟 연령대: 60대, 70대, 80대 한국인 또는 동아시아 시니어 묘사 (Korean/East Asian senior)
3. 구체적 공간: 실제 안전 생활공간 묘사 (욕실, 침실, 거실, 주방, 현관 등)
4. 분위기: 자연스러운 홈 라이프스타일 사진 분위기 (Warm and trustworthy atmosphere, natural lifestyle photograph)
5. 조명: 부드럽고 따뜻한 조명 설계 (Soft warm lighting, gentle natural sunlight)
6. 카메라 구도: 편안한 카메라 구도 (Eye-level angle, medium shot, close-up)
7. 자연스러운 배치: 과장된 합성 광고가 아닌 실제 가정집 인테리어 속에 상품이 자연스레 융합되어 나타나는 연출
8. No text: 프롬프트에 텍스트 배제 지시 삽입
9. No logo: 로고 배제 지시 삽입
10. No watermark: 워터마크 및 글자 기재 차단 지시 삽입

[제목 생성 6대 유형 및 작성 조건]
제시된 제목 후보 5개는 다음 6가지 유형 중 본문 및 키워드 상황에 가장 알맞은 5가지를 선정하여 각각 다른 형태(유형)로 25~45자 이내로 창작해야 합니다.
1. 문제 해결형 (예: 혼자 사는 부모님 집에 꼭 필요한 안심용품 7가지)
2. 선물 추천형 (예: 70대 어머니 생신선물, 실용적인 생활용품 중심으로 고르는 법)
3. 체크리스트형 (예: 부모님 집 욕실 안전을 위해 확인해야 할 생활용품 체크리스트)
4. 계절형 (예: 겨울철 부모님 방에 있으면 좋은 온열 생활용품)
5. 비교형 (예: 부모님 발마사지기 고를 때 꼭 봐야 할 기준)
6. 공감형 (예: 자주 찾아뵙지 못하는 부모님께 챙겨드리면 좋은 안심용품)

제목 작성 5대 규칙:
- 메인 키워드('{main_keyword}')를 문맥 속에 아주 자연스럽게 녹여냅니다.
- 너무 상업적이거나 광고처럼 보이지 않게 정보성 톤앤매너를 지킵니다.
- 클릭을 유도하되 절대 과장이나 낚시를 하지 않습니다.
- "무조건", "대박", "완전 추천", "최고", "완벽" 같은 과장 단어는 절대 사용을 금합니다.
- 각 제목의 총 글자 수는 공백 포함 반드시 **25자 이상 45자 이하**로 제한됩니다.

[출력 형식]
아래의 JSON 구조와 필드명을 정확히 지켜서 출력하세요. JSON 외부에는 어떠한 텍스트도 절대 반환하지 마세요.

{{
  "title_candidates": [
    {{"type": "문제 해결형", "title": "25~45자 제한을 지키고 메인 키워드를 넣은 문제 해결 제목"}},
    {{"type": "선물 추천형", "title": "25~45자 제한을 지킨 선물 추천형 제목"}},
    {{"type": "체크리스트형", "title": "25~45자 제한을 지킨 체크리스트형 제목"}},
    {{"type": "계절형", "title": "25~45자 제한을 지킨 계절형 제목"}},
    {{"type": "공감형", "title": "25~45자 제한을 지킨 공감형 제목"}}
  ],
  "selected_title": "위 5개 제목 후보의 'title' 중 가장 자연스러운 추천 제목 1개 선택 (글자수 25~45자 필수 만족)",
  "introduction": "자녀의 관점에서 부모님의 일상 위험 상황을 깊이 공감하고 걱정 어린 오프닝으로 시작하는 도입부 본문. (2~4문장마다 무조건 문단을 나누어 줄바꿈할 것)",
  "subtitles": [
    "소제목 1 (핵심 문제 제시)",
    "소제목 2 (안전 및 실용성 가치)",
    "소제목 3 (체크 가이드)",
    "소제목 4 (상품군 소개)",
    "소제목 5 (필요시 추가 소제목)"
  ],
  "body_sections": [
    "소제목 1에 매칭되는 상세 본문. 한 문단은 2~4문장 이내로 짧게 작성하고 문단 간 줄바꿈을 크게 넣을 것.",
    "소제목 2에 매칭되는 상세 본문...",
    "소제목 3에 매칭되는 상세 본문...",
    "소제목 4에 매칭되는 상세 본문...",
    "소제목 5에 매칭되는 상세 본문..."
  ],
  "shopping_link_paragraph": "쇼핑 정보 및 제안 뉘앙스를 담은 자연스러운 한 문장 내외의 초안 문장.",
  "selection_criteria": "용품을 선택할 때 꼭 체크해야 할 본질적인 성능/치수/재질 기준 정리 문단 (짧고 쉬운 문장으로 전개).",
  "precautions": "사용할 때 주의해야 할 점 (치료 단정 표현 금지, 효과보장 등의 단어 사용 금지, 안전 가이드 느낌으로 2~3문장 서술).",
  "conclusion": "부모님이 매일을 건강하고 안전하게 지내기를 기원하는 자녀의 소망 어린 정감 가득한 맺음말.",
  "hashtags": ["메인키워드", "연관태그2", "태그3", "태그4", "태그5", "태그6", "태그7", "태그8", "태그9", "태그10"],
  "image_prompts": [
    {{
      "prompt": "Detailed English image generation prompt for a natural photograph. Must portray a 60-80yo Korean/East Asian senior in a warm domestic scene (like using a product naturally in bedroom/bathroom/living room/kitchen). Soft natural lighting, camera angle, realistic product integration, no text, no logo, no watermark.",
      "filename": "english_lowercase_filename_01.jpg",
      "alt_text": "한국 시니어가 따뜻한 공간에서 상품을 자연스럽게 사용/선물받는 장면을 사실적으로 한글 서술"
    }},
    {{
      "prompt": "Second English image generation prompt...",
      "filename": "english_lowercase_filename_02.jpg",
      "alt_text": "..."
    }},
    {{
      "prompt": "Third English image generation prompt...",
      "filename": "english_lowercase_filename_03.jpg",
      "alt_text": "..."
    }}
  ]
}}
"""
        
        response_text = call_gemini_rest_api(api_key, prompt).strip()
        
        if response_text.startswith("```json"):
            response_text = re.sub(r"^```json\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
        elif response_text.startswith("```"):
            response_text = re.sub(r"^```\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
            
        data = json.loads(response_text)
        
        if len(data.get("subtitles", [])) != len(data.get("body_sections", [])):
            min_len = min(len(data.get("subtitles", [])), len(data.get("body_sections", [])))
            data["subtitles"] = data["subtitles"][:min_len]
            data["body_sections"] = data["body_sections"][:min_len]
            
        return data
        
    except json.JSONDecodeError as je:
        print(f"JSON 파싱 실패: {je}")
        print(f"원본 응답: {response_text}")
        return {"error": "AI의 응답 형식을 JSON으로 파싱하는 데 실패했습니다. 다시 시도해 주세요."}
    except Exception as e:
        print(f"블로그 글 생성 오류: {e}")
        return {"error": f"글 생성 중 에러가 발생했습니다: {str(e)}"}


def regenerate_titles(api_key: str, main_keyword: str, content: str, products: str) -> dict:
    """
    본문과 키워드를 기반으로 6대 유형 조건(25~45자 제한)을 만족하는 제목 5종을 단독 재생성합니다.
    """
    if not api_key:
        return {"error": "API Key가 유효하지 않습니다."}
    try:
        
        prompt = f"""
당신은 네이버 블로그 전문 카피라이터입니다.
제시된 본문 내용과 상품군 정보를 기반으로, 네이버 검색 노출에 최적인 제목 후보 5개와 그 중 최적의 최종 제목 1개를 다시 지어주세요.

[본문 내용]
{content}

[소개 상품군]
{products}

[제목 생성 6대 유형 및 작성 조건]
제시된 제목 후보 5개는 다음 6가지 유형 중 본문 및 키워드 상황에 가장 알맞은 5가지를 선정하여 각각 다른 형태(유형)로 25~45자 이내로 창작해야 합니다.
1. 문제 해결형 (예: 혼자 사는 부모님 집에 꼭 필요한 안심용품 7가지)
2. 선물 추천형 (예: 70대 어머니 생신선물, 실용적인 생활용품 중심으로 고르는 법)
3. 체크리스트형 (예: 부모님 집 욕실 안전을 위해 확인해야 할 생활용품 체크리스트)
4. 계절형 (예: 겨울철 부모님 방에 있으면 좋은 온열 생활용품)
5. 비교형 (예: 부모님 발마사지기 고를 때 꼭 봐야 할 기준)
6. 공감형 (예: 자주 찾아뵙지 못하는 부모님께 챙겨드리면 좋은 안심용품)

제목 작성 5대 규칙:
- 메인 키워드('{main_keyword}')를 문맥 속에 아주 자연스럽게 녹여냅니다.
- 너무 상업적이거나 광고처럼 보이지 않게 정보성 톤앤매너를 지킵니다.
- 클릭을 유도하되 절대 과장이나 낚시를 하지 않습니다.
- "무조건", "대박", "완전 추천", "최고", "완벽" 같은 과장 단어는 절대 사용을 금합니다.
- 각 제목의 총 글자 수는 공백 포함 반드시 **25자 이상 45자 이하**로 제한됩니다.

[출력 형식]
아래의 JSON 구조와 필드명을 정확히 지켜서 출력하세요. JSON 외부에는 어떠한 텍스트도 절대 반환하지 마세요.

{{
  "title_candidates": [
    {{"type": "문제 해결형", "title": "25~45자 제한을 지키고 메인 키워드를 넣은 문제 해결 제목"}},
    {{"type": "선물 추천형", "title": "25~45자 제한을 지킨 선물 추천형 제목"}},
    {{"type": "체크리스트형", "title": "25~45자 제한을 지킨 체크리스트형 제목"}},
    {{"type": "계절형", "title": "25~45자 제한을 지킨 계절형 제목"}},
    {{"type": "공감형", "title": "25~45자 제한을 지킨 공감형 제목"}}
  ],
  "selected_title": "위 5개 제목 후보의 'title' 중 가장 자연스러운 추천 제목 1개 선택 (글자수 25~45자 필수 만족)"
}}
"""
        response_text = call_gemini_rest_api(api_key, prompt).strip()
        if response_text.startswith("```json"):
            response_text = re.sub(r"^```json\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
        elif response_text.startswith("```"):
            response_text = re.sub(r"^```\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
            
        import json
        return json.loads(response_text)
    except Exception as e:
        return {"error": f"제목 단독 재생성 실패: {str(e)}"}


def regenerate_image_prompts(api_key: str, content: str, products: str) -> dict:
    """
    본문과 상품군을 연동하여 영문 AI 이미지 생성용 프롬프트 3종을 단독 재생성합니다.
    """
    if not api_key:
        return {"error": "API Key가 유효하지 않습니다."}
    try:
        
        prompt = f"""
당신은 네이버 블로그에 사용할 포토그래픽 아티스트입니다.
제시된 본문 내용과 상품 정보를 바탕으로 블로그 이미지용 영문 AI 이미지 프롬프트 3종과 파일명, 한글 alt 텍스트를 다시 지어주세요.

[본문 내용]
{content}

[소개 상품군]
{products}

[AI 이미지 프롬프트 생성 10대 조건]
1. 장면 테마: 부모님이 상품을 사용 중인 일상 / 자녀가 부모님께 선물을 전달하는 장면 / 독거 시니어의 아늑한 일상 생활
2. 타겟 연령대: 60대, 70대, 80대 한국인 또는 동아시아 시니어 묘사 (Korean/East Asian senior)
3. 구체적 공간: 실제 안전 생활공간 묘사 (욕실, 침실, 거실, 주방, 현관 등)
4. 분위기: 자연스러운 홈 라이프스타일 사진 분위기 (Warm and trustworthy atmosphere, natural lifestyle photograph)
5. 조명: 부드럽고 따뜻한 조명 설계 (Soft warm lighting, gentle natural sunlight)
6. 카메라 구도: 편안한 카메라 구도 (Eye-level angle, medium shot, close-up)
7. 자연스러운 배치: 과장된 합성 광고가 아닌 실제 가정집 인테리어 속에 상품이 자연스레 융합되어 나타나는 연출
8. No text: 프롬프트에 텍스트 배제 지시 삽입
9. No logo: 로고 배제 지시 삽입
10. No watermark: 워터마크 및 글자 기재 차단 지시 삽입

[출력 형식]
아래의 JSON 구조와 필드명을 정확히 지켜서 출력하세요. JSON 외부에는 어떠한 텍스트도 절대 반환하지 마세요.

{{
  "image_prompts": [
    {{
      "prompt": "Detailed English image generation prompt for a natural photograph. Must portray a 60-80yo Korean/East Asian senior in a warm domestic scene. Soft natural lighting, camera angle, realistic product integration, no text, no logo, no watermark.",
      "filename": "english_lowercase_filename_01.jpg",
      "alt_text": "한국 시니어가 상품을 사용하는 일상을 구체적으로 한글 서술"
    }},
    {{
      "prompt": "Second prompt...",
      "filename": "english_lowercase_filename_02.jpg",
      "alt_text": "..."
    }},
    {{
      "prompt": "Third prompt...",
      "filename": "english_lowercase_filename_03.jpg",
      "alt_text": "..."
    }}
  ]
}}
"""
        response_text = call_gemini_rest_api(api_key, prompt).strip()
        if response_text.startswith("```json"):
            response_text = re.sub(r"^```json\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
        elif response_text.startswith("```"):
            response_text = re.sub(r"^```\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)
            
        import json
        return json.loads(response_text)
    except Exception as e:
        return {"error": f"이미지 프롬프트 단독 재생성 실패: {str(e)}"}
