import os
os.environ["API_VERSION"] = "v1"
import json
import urllib.request
import urllib.parse
import re
import random
import google.generativeai as genai

def get_stable_hash(s):
    """파이썬 프로세스 재실행 및 세션 리런 시에도 언제나 동일한 정수 해시값을 보장합니다."""
    return sum(ord(c) * (i + 1) for i, c in enumerate(s))


# Matrix 조합 성분 정의
MATRIX_AGES = ["60대", "70대", "80대", "실버세대", "노령층"]
MATRIX_TARGETS = ["어머니", "아버지", "부모님", "혼자 사는 어머니", "혼자 사는 아버지", "독거노인 부모님"]
MATRIX_SITUATIONS = ["생신선물", "실용 선물", "명절선물", "겨울 선물", "여름 선물", "안심용품", "안전용품", "낙상 예방용"]

def load_products_db():
    """로컬 products_db.json 파일을 불러옵니다."""
    try:
        with open("products_db.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def fetch_naver_autocomplete(keyword):
    """네이버 자동완성 API를 통해 실시간 검색 확장어를 수집합니다."""
    enc_keyword = urllib.parse.quote(keyword)
    url = f"https://ac.search.naver.com/ac?q={enc_keyword}&r_format=json&t_koreng=1&q_enc=utf-8&r_enc=utf-8&r_unicode=0&t_word=1"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            items = res_data.get("items", [])
            keywords = []
            if items and len(items) > 0:
                for suggestion in items[0]:
                    if suggestion and len(suggestion) > 0:
                        keywords.append(suggestion[0])
            return keywords
    except Exception:
        return []

def fetch_naver_related_keywords(keyword):
    """네이버 통합검색 결과에서 연관검색어를 수집합니다."""
    enc_keyword = urllib.parse.quote(keyword)
    url = f"https://search.naver.com/search.naver?query={enc_keyword}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            matches = re.findall(r'<span class="tit">([^<]+)</span>', html)
            if not matches:
                matches = re.findall(r'<a[^>]*class="[^"]*keyword[^"]*"[^>]*>([^<]+)</a>', html)
            keywords = list(dict.fromkeys([m.strip() for m in matches if m.strip()]))
            return keywords
    except Exception:
        return []

def expand_keyword_matrix(base_keyword, api_key):
    """
    기본 키워드를 입력받아 네이버 수집 정보 + Matrix 조합 분석을 수행하고,
    Gemini AI(또는 로컬 폴백)를 사용해 구체적 롱테일 키워드 10개와 상품 매칭 결과를 생성합니다.
    """
    products_db = load_products_db()
    
    # 1. 1차 크롤링 정보 수집
    crawled_pool = []
    crawled_pool.extend(fetch_naver_autocomplete(base_keyword))
    crawled_pool.extend(fetch_naver_related_keywords(base_keyword))
    crawled_pool = list(dict.fromkeys([k.strip() for k in crawled_pool if k.strip()]))
    
    # 2. 로컬 상품 리스트업
    product_list = []
    for cat, items in products_db.items():
        for p_name in items.keys():
            product_list.append(p_name)
            
    # 3. API Key가 없을 때의 로컬 자율 합성 폴백 가동
    if not api_key:
        random.seed(get_stable_hash(base_keyword))
        fallback_results = []

        
        # 10대 구체적 롱테일 키워드 결합 생성
        templates = [
            f"70대 어머니 실용적인 생신선물로 좋은 {random.choice(product_list)}",
            f"60대 아버지 은퇴 축하 선물 추천 {random.choice(product_list)}",
            f"혼자 사는 어머니 안방 안전을 위한 {random.choice(product_list)} 설치",
            f"독거노인 부모님 가을철 면역력을 돕는 건강 용품",
            f"부모님 겨울철 빙판길 안전 예방 용품 리스트",
            f"시니어 부모님 관절 통증을 줄여주는 무릎 용품",
            f"혼자 계신 부모님 주방 화재 예방 타이머 선물",
            f"부모님 화장실 미끄럼 방지를 위한 안전 패드 추천",
            f"어두운 밤 부모님 침실 낙상 예방 센서등 추천",
            f"연로하신 부모님 노안 맞춤 대화면 혈압계 고르는 법"
        ]
        
        # 실제 입력된 base_keyword 맥락을 반영하도록 일부 치환
        cleaned_base = base_keyword.replace("선물", "").replace("용품", "").strip()
        for idx, temp in enumerate(templates):
            kw_candidate = temp
            if cleaned_base and cleaned_base not in kw_candidate:
                # 키워드 접두사 또는 접미사 병합
                kw_candidate = f"{cleaned_base} 맞춤 {kw_candidate}"
                
            # 상품 매칭 역추적
            matched_prod = "직접 입력"
            for p in product_list:
                if p in kw_candidate or any(word in kw_candidate for word in p.split()):
                    matched_prod = p
                    break
            if matched_prod == "직접 입력" and product_list:
                matched_prod = random.choice(product_list)
                
            fallback_results.append({
                "rank": idx + 1,
                "keyword": kw_candidate[:40],
                "product": matched_prod,
                "post_type": random.choice(["부모님 선물 추천형", "시니어 생활문제 해결형", "건강관리 생활용품형"]),
                "reason": f"기본어 '{base_keyword}'에 인구통계 대상과 구체적인 {matched_prod} 상품 속성을 결합하여 발굴한 실속 노출용 롱테일 키워드입니다."
            })
            
        return {"expanded_keywords": fallback_results}

    # 4. AI(Gemini) 지능형 롱테일 매칭
    import os
    os.environ["API_VERSION"] = "v1"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-1.5-flash')

    
    prompt = f"""
    당신은 블로그 키워드 마케팅 및 노출 전문가입니다.
    
    [기본 검색어]: "{base_keyword}"
    [최근 네이버 확장 단어 후보]: {crawled_pool[:15]}
    [매칭 가능한 상품 DB 목록]: {product_list[:30]}
    
    [수행 작업]
    위 정보를 융합하여 다음 규칙에 맞는 '구체적인 롱테일(Long-tail) 키워드 10개'를 확장하고 각 키워드별 매칭 상품군을 선정하여 JSON으로만 반환해 주세요.
    
    [롱테일 키워드 확장 규칙]
    1. 경쟁이 세고 포괄적인 키워드(예: '부모님 선물')는 철저히 배제합니다.
    2. 연령대(예: 70대, 80대), 대상(예: 어머니, 혼자 사는 아버지), 상황(예: 생신, 겨울, 화장실 안전), 상품군(예: 침대 가드, 온열 찜질기) 정보를 기본 검색어와 자연스럽게 조합하여 검색 구체성이 높은 롱테일 키워드를 10개 도출합니다.
    3. 각 확장 키워드에는 반드시 우리 상품 DB에 존재하는 구체적인 'product'명을 정확하게 일대일 매칭해 줍니다.
    4. 예상 블로그 글 유형('post_type')도 함께 정의해 주세요.
    
    반드시 마크다운 코드 블록(```json) 없이 순수한 JSON 텍스트로만 대답해 주세요.
    JSON 스키마 예시:
    {{
      "expanded_keywords": [
        {{
          "rank": 1,
          "keyword": "70대 어머니 생신선물 온열찜질 벨트 추천",
          "product": "온열찜질기",
          "post_type": "부모님 선물 추천형",
          "reason": "최근 70대 고령 어머니 타겟의 무릎/허리 찜질 클릭량이 늘고 있어 가장 적합한 롱테일 키워드 조합입니다."
        }}
      ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        raw_text = re.sub(r"^```json\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        
        result_json = json.loads(raw_text)
        return result_json
    except Exception as e:
        return {"error": f"AI 키워드 확장 실패: {str(e)}"}

if __name__ == "__main__":
    # 단독 테스트 검증
    print("기본 키워드 '부모님 선물'로 롱테일 확장 테스트 진행...")
    res = expand_keyword_matrix("부모님 선물", "")
    print(json.dumps(res, ensure_ascii=False, indent=2))
