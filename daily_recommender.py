import json
import topic_scorer

def get_today_recommendations():
    """
    최근 수집된 트렌드 데이터를 스코어링하여 점수 상위 20개 중 
    오늘 작성하기 가장 좋은 5대 주제를 선정하고, 각 주제별 제목 후보 5개와 쇼커 연계를 정의해 반환합니다.
    """
    # 1. 상위 스코어 후보군 20개 로드
    scored_all = topic_scorer.calculate_topic_scores()
    top_20 = scored_all[:20]
    
    # 2. 그중 최상위 5개 엄선
    top_5 = top_20[:5]
    
    recommendations = []
    
    for item in top_5:
        kw = item.get("keyword", "")
        prod = item.get("product", "직접 입력")
        cat = item.get("category", "부모님 선물")
        post_type = item.get("post_type", "부모님 선물 추천형")
        reason = item.get("reason", "최근 검색 유입과 계절 기상 조건이 부모님 맞춤 상품군 노출에 가장 적합하여 추천합니다.")
        shocker_guide = item.get("shocker_link_guide", "")
        rank = item.get("rank", 1)
        total_score = item.get("total_score", 90.0)
        
        # 3. 각 주제마다 노출이 잘 되는 글 제목 후보 5개 빌드
        # 모든 제목 후보에 반드시 메인 키워드(kw)가 포함되도록 최적화 (SEO 강점 확보 및 혼선 방지)
        title_candidates = [
            f"부모님 안전을 지키는 {kw} 선택 기준 및 추천 가이드",
            f"60대 70대 부모님 실용 선물 극찬! {kw} ({prod}) 솔직 분석",
            f"혼자 사는 부모님 집 {kw} 설치로 낙상 사고 안심 예방하는 법",
            f"자녀의 걱정을 덜어주는 효도용 {kw} ({prod}) 고르는 3가지 기준",
            f"부모님 깜짝 생신선물! {kw} 추천과 자녀들의 실제 사용 후기"
        ]
        
        # 카테고리가 욕실이나 침실 안전일 때는 안전/안심 관련 타이틀로 추가 보정
        if "욕실" in cat or "침실" in cat or "안전" in kw:
            title_candidates[0] = f"부모님 욕실 침실 낙상 예방을 위한 {kw} 안심 가이드"
            title_candidates[4] = f"연로하신 부모님 안전 필수품! {kw} 추천 및 설치 팁"

            
        recommendations.append({
            "rank": rank,
            "title": f"부모님 안전과 실용을 돕는 {kw} 추천 및 가이드",
            "keyword": kw,
            "product": prod,
            "post_type": post_type,
            "reason": reason,
            "shocker_link_guide": shocker_guide,
            "titles_pool": title_candidates,
            "total_score": total_score
        })
        
    return recommendations

if __name__ == "__main__":
    # 단독 테스트 검증
    print("오늘의 추천 주제 Best 5 추출 테스트...")
    recs = get_today_recommendations()
    for item in recs:
        print(f"\n{item['rank']}위 주제:")
        print(f"- 추천 주제: {item['title']} (최종 점수: {item['total_score']}점)")
        print(f"- 메인 키워드: {item['keyword']}")
        print(f"- 관련 상품군: {item['product']}")
        print(f"- 글 유형: {item['post_type']}")
        print(f"- 추천 이유: {item['reason']}")
        print(f"- 쇼커 링크 연결 방식: {item['shocker_link_guide']}")
        print("- 제목 후보 5개:")
        for t_idx, title in enumerate(item["titles_pool"]):
            print(f"  {t_idx+1}) {title}")
