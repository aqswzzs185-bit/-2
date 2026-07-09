import json
import os
import random
from datetime import datetime

def load_keywords_seed_db():
    """keywords_seed_db.json 파일을 로드합니다."""
    try:
        with open("keywords_seed_db.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def load_products_db():
    """products_db.json 파일을 로드합니다."""
    try:
        with open("products_db.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def load_trend_data():
    """trend_data.json 파일을 로드합니다."""
    if os.path.exists("trend_data.json"):
        try:
            with open("trend_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def calculate_topic_scores():
    """
    수집된 키워드와 확장 키워드 후보 전체를 불러와
    7대 가중치 지표에 따라 채점(100점 만점)하고 내림차순 정렬하여 상위 추천 보드 리스트를 반환합니다.
    """
    seed_db = load_keywords_seed_db()
    products_db = load_products_db()
    trend_history = load_trend_data()
    
    # 최근 날짜의 트렌드 데이터 로드
    latest_trends = {}
    if trend_history:
        latest_date = max(trend_history.keys())
        latest_trends = trend_history.get(latest_date, {})
        
    flat_candidates = []
    
    # 6대 카테고리 시드 순회하며 후보군 취합
    for cat, items in seed_db.items():
        for item in items:
            flat_candidates.append(item)
            
    # 2. 7대 지표 정밀 채점 개시
    scored_list = []
    month = datetime.now().month
    
    # 상품 DB의 모든 서브 상품군 평탄화
    flat_products = []
    for c_name, p_items in products_db.items():
        flat_products.extend(p_items.keys())
        
    for idx, item in enumerate(flat_candidates):
        kw = item.get("keyword", "")
        cat = item.get("category", "")
        prod = item.get("related_product", "")
        expected_post_type = item.get("expected_post_type", "부모님 선물 추천형")
        
        # 1. 트렌드 점수 (25점 만점)
        # trend_data.json의 최근 클릭 점수 및 상승률 조회
        trend_item = latest_trends.get(kw, {})
        if trend_item:
            # 실시간 급상승 감지 시 가산
            weekly_inc = trend_item.get("weekly_increase", 0.0)
            if weekly_inc >= 25.0:
                trend_score = 25.0
            elif weekly_inc >= 10.0:
                trend_score = 22.0
            elif weekly_inc >= 0.0:
                trend_score = 18.0
            else:
                trend_score = 14.0
        else:
            # 트렌드 데이터가 없을 시 기본 16~22점 사이 자동 배정
            random.seed(hash(kw) + 1)
            trend_score = round(random.uniform(16.0, 22.0), 1)
            
        # 2. 구매 의도 점수 (25점 만점)
        # 키워드 내 실구매 의도 어휘 판정
        buy_intent_words = ["선물", "추천", "비교", "고르는", "방지", "바", "의자", "센서등", "보호대", "안방", "안심"]
        if any(w in kw for w in buy_intent_words):
            buy_intent_score = 25.0
        else:
            buy_intent_score = 17.0
            
        # 3. 쇼커 링크 연결 점수 (20점 만점)
        # products_db에 키워드가 지목한 세부 상품명이 실재 매핑되어 있는지 여부
        has_matched_product = False
        for p in flat_products:
            if p in kw or p in prod or any(word in kw for word in p.split()):
                has_matched_product = True
                prod = p # 롱테일 대응을 위한 실제 상품명 정밀 동기화
                break
        shocker_score = 20.0 if has_matched_product else 12.0
        
        # 4. 경쟁 회피 점수 (15점 만점)
        # 구체적인 롱테일 형태(글자수 12자 이상 + 수식어 포함) 판정
        is_longtail = len(kw) >= 12 or any(target in kw for target in ["60대", "70대", "80대", "혼자 사는", "독거노인", "침실", "욕실"])
        avoid_competition_score = 15.0 if is_longtail else 7.0
        
        # 5. 계절성 점수 (10점 만점)
        season_rules = {
            (1, 2): ["겨울 부모님 선물", "온열찜질기", "전기요", "보온용품", "미끄럼 방지 신발", "욕실 온도차 주의"],
            (3, 4): ["봄맞이 부모님 생활용품", "미세먼지", "공기청정", "외출용품", "무릎보호대", "걷기 보조용품"],
            (5,): ["어버이날 선물", "부모님 선물", "건강관리 생활용품", "마사지기", "혈압계", "실용 선물"],
            (6, 7, 8): ["여름 부모님 선물", "장마철 습기 관리", "욕실 미끄럼 방지", "냉감용품", "선풍기", "제습기", "물빠짐 매트", "시니어 여름 생활용품"],
            (9,): ["추석 부모님 선물", "명절 선물", "부모님 실용 선물", "건강관리용품", "안마용품"],
            (10, 11): ["환절기 부모님 생활용품", "보온용품", "가습기", "침실용품", "수면용품"],
            (12,): ["겨울 부모님 선물", "온열용품", "전기요", "손발 보온용품", "연말 부모님 선물"]
        }
        
        current_season_kws = []
        for m_tuple, kws in season_rules.items():
            if month in m_tuple:
                current_season_kws = kws
                break
                
        is_current_season = any(
            w in kw or w in prod or any(sub in kw for sub in w.split())
            for w in current_season_kws
        )
        
        is_seasonal = item.get("is_seasonal", False)
        if is_seasonal:
            if is_current_season:
                season_score = 10.0
            else:
                season_score = 3.0
        else:
            if is_current_season:
                season_score = 10.0
            else:
                season_score = 7.0

            
        # 6. 글 작성 용이성 점수 (3점 만점)
        # 구조화가 뛰어난 문제해결형/비교형은 3점, 단순형은 1.5점
        if expected_post_type in ["시니어 생활문제 해결형", "비교 추천형", "혼자 사는 부모님 안심용품형"]:
            writing_ease_score = 3.0
        else:
            writing_ease_score = 2.0
            
        # 7. 부모님 공감 점수 (2점 만점)
        # 자녀 걱정 포인트(안전, 안심, 예방, 척추, 시림, 꿀잠 등)가 짙게 녹아있으면 2점 만점
        empathy_words = ["안전", "안심", "예방", "시림", "걱정", "효도", "낙상", "미끄럼", "혼자 사는", "독거"]
        if any(w in kw for w in empathy_words) or len(item.get("empathy_point", "")) > 30:
            empathy_score = 2.0
        else:
            empathy_score = 1.0
            
        # 8. 최종 합산 스코어 (100점 만점)
        total_score = round(
            trend_score + 
            buy_intent_score + 
            shocker_score + 
            avoid_competition_score + 
            season_score + 
            writing_ease_score + 
            empathy_score,
            1
        )
        
        # 9. 동적 쇼커 링크 연결 가이드 작문
        if shocker_score == 20.0:
            if any(w in prod for w in ["마사지기", "찜질기", "안마", "혈압계"]):
                shocker_guide = f"본문 중반 도입부 {prod} 뭉친 부위 해결 앵커 텍스트로 1회, 본문 결론부에 자연스러운 상세 스펙 구매 링크로 1회 삽입"
            elif any(w in prod for w in ["매트", "손잡이", "의자", "센서등", "안전바"]):
                shocker_guide = f"본문 전반 도입부 낙상 사고 예방을 위한 {prod} 앵커 텍스트로 1회, 본문 후반부에 제품 정보 링크로 1회 삽입"
            else:
                shocker_guide = f"본문 중간과 하단에 각각 {prod}의 실용적인 기능을 자연스럽게 설명하며 쇼커 앵커 텍스트 링크로 2회 삽입"
        else:
            shocker_guide = "본문 도입부 금지 규칙 준수 하에, 포스팅 중간 맥락에 맞는 쇼커 쿠팡 파트너스 링크 1회 안전 텍스트 삽입"
            
        # 추천 이유 조합
        reason = item.get("empathy_point", "")
        if len(reason) > 60:
            reason = reason[:57] + "..."
            
        scored_list.append({
            "keyword": kw,
            "category": cat,
            "product": prod,
            "post_type": expected_post_type,
            "total_score": total_score,
            "reason": reason,
            "shocker_link_guide": shocker_guide
        })
        
    # 최종 점수 내림차순 정렬
    scored_list.sort(key=lambda x: x["total_score"], reverse=True)
    
    # 랭킹 부여 및 상위 5대 추천 가이드
    for idx, item in enumerate(scored_list):
        item["rank"] = idx + 1
        item["title"] = f"부모님 안전을 지키는 {item['keyword']} 선택 기준 및 추천"
        
    return scored_list

if __name__ == "__main__":
    # 단독 테스트 검증
    print("7대 평가 가중치 합산 스코어링 모듈 가동...")
    scored = calculate_topic_scores()
    print(f"총 {len(scored)}개 후보 채점 완료.")
    print("탑 3 추천 리포트 출력:")
    for item in scored[:3]:
        print(f"\n[{item['rank']}위] 점수: {item['total_score']}점 | 키워드: {item['keyword']}")
        print(f"- 상품: {item['product']} | 유형: {item['post_type']}")
        print(f"- 추천사유: {item['reason']}")
        print(f"- 쇼커가이드: {item['shocker_link_guide']}")
