import json
import re
from generator import call_gemini_rest_api

def evaluate_seo_and_readability(
    api_key: str, 
    title: str, 
    content: str, 
    tags: list, 
    main_keyword: str, 
    char_count: str, 
    products: str
) -> dict:
    """
    네이버 블로그 검색 엔진 최적화(SEO) 기준 및 가독성 10대 조건을 채점하고 수정 보완 필요 항목을 도출합니다.
    """
    # 1. 로컬 기반 객관적 계측
    issues = []
    
    # 규칙 1: 제목에 메인 키워드 포함 검사
    title_has_kw = main_keyword.strip().lower() in title.lower()
    if not title_has_kw:
        issues.append("제목에 메인 키워드가 자연스럽게 들어있지 않습니다. (검색 노출 불리)")
        
    # 규칙 2: 첫 300자 내에 메인 키워드 포함 검사
    first_300 = content[:300]
    first_300_has_kw = main_keyword.strip().lower() in first_300.lower()
    if not first_300_has_kw:
        issues.append("원고 극초반(첫 300자 이내)에 메인 키워드가 언급되지 않았습니다.")
        
    # 규칙 3: 본문 키워드 빈도 조절 (너무 적거나 과다하면 노출 지수 하락)
    content_kw_count = len(re.findall(re.escape(main_keyword.strip()), content, re.IGNORECASE))
    if content_kw_count == 0:
        issues.append("본문 내에 메인 키워드가 단 한 번도 사용되지 않았습니다.")
    elif content_kw_count > 8:
        issues.append(f"본문 내 메인 키워드 빈도가 과도합니다 (총 {content_kw_count}회). 스팸 필터 회피를 위해 3~6회 이내로 조율해 주세요.")
        
    # 규칙 5: 소제목 개수 계측 (4개 이상)
    subtitles_found = re.findall(r"(■|📌|⚠️|■\s+[0-9]+|📌\s+[0-9]+)", content)
    sub_count = len(subtitles_found)
    if sub_count < 4:
        issues.append(f"본문의 소제목(가독성 단락 구분자) 개수가 {sub_count}개로 부족합니다. (최소 4개 이상 권장)")
        
    # 규칙 8: 해시태그 개수 (5~10개)
    tags_count = len(tags)
    if tags_count < 5 or tags_count > 10:
        issues.append(f"등록된 해시태그 수가 {tags_count}개입니다. 네이버 블로그에 효과적인 5~10개 범위에 맞게 재정비가 필요합니다.")
        
    # 규칙 9: 글자 수 일치 검사
    target_len = int(re.sub(r"[^0-9]", "", char_count))
    current_len = len(content)
    if current_len < (target_len - 300):
        issues.append(f"작성된 본문 분량(공백 포함 약 {current_len}자)이 선택하신 목표 분량({char_count})에 다소 부족합니다.")

    # 2. AI 정밀 심층 판독 (주관적 및 흐름성 검증)
    if not api_key:
        # 로컬 기본 판정 반환
        return {
            "seo_score": 70 if issues else 100,
            "readability_score": 80,
            "ad_risk": "보통",
            "issues": issues,
            "need_auto_fix": len(issues) > 0
        }
        
    try:
        
        prompt = f"""
당신은 네이버 블로그 전문 마케팅 기획자이자 포스팅 SEO 검수 엔진입니다.
제시된 제목과 본문, 해시태그를 네이버 검색 로직(C-Rank, D.I.A+ 로직)과 독자 가독성 기준에 맞춰 100점 만점으로 공정히 평가해 주세요.

[평가 대상 원고]
- 메인 키워드: {main_keyword}
- 소개 상품군: {products}
- 목표 글자 수: {char_count}
- 포스팅 원고:
제목: {title}
본문:
{content}
태그: {', '.join(tags)}

[10대 검수 조건 리스트]
1. 제목에 메인 키워드 자연스럽게 포함
2. 첫 300자 안에 메인 키워드 유입
3. 본문 전체에 메인 키워드 과다 도배 방지 (전체 3~6회 수준 최적)
4. 소개할 상품군 등 관련 보조 키워드 매끄러운 융합
5. 소제목이 4개 이상 구성되어 시인성이 좋은지
6. 한 문단이 너무 길어 모바일 화면에서 숨막히지 않는지 (한 문단 2~4문장 이내 규정)
7. 모바일 뷰에 알맞은 시원한 문단 나눔(엔터 줄바꿈)
8. 해시태그 5~10개 유지
9. 글자 수가 목표치({char_count}) 근사치인지
10. 본문과 조화를 이루며 구매 압박 없는 쇼커 링크 융합

[출력 규격]
반드시 아래의 JSON 구조로만 응답하세요. 다른 부가적인 텍스트는 절대 작성 금지입니다.

{{
  "seo_score": 0~100 사이 정수 (메인/보조 키워드 배치, 해시태그 개수, C-Rank 노출지수 종합 채점),
  "readability_score": 0~100 사이 정수 (문단 쪼개기, 모바일 줄바꿈, 문장의 가독성 채점),
  "ad_risk": "낮음 또는 보통 또는 높음",
  "issues": [
    "AI 판단에 의해 지적된 추가 수정 필요 항목 (예: '본문 3문단이 너무 길어 모바일 줄바꿈 보강이 필요함' 등)"
  ]
}}
"""
        response_text = call_gemini_rest_api(api_key, prompt).strip()
        data = json.loads(response_text)
        
        # 로컬에서 감지된 문제들과 AI가 감지한 문제들을 영리하게 병합하여 신뢰성 증대
        merged_issues = list(set(issues + data.get("issues", [])))
        data["issues"] = merged_issues
        data["need_auto_fix"] = len(merged_issues) > 0
        
        return data
        
    except Exception as e:
        print(f"SEO 검수 중 오류 발생: {e}")
        return {
            "seo_score": 80,
            "readability_score": 75,
            "ad_risk": "보통",
            "issues": issues if issues else ["검수 엔진 가동 중 일시적인 API 대기가 발생하여 로컬 룰로 간이 평가했습니다."],
            "need_auto_fix": len(issues) > 0
        }

def auto_fix_content(
    api_key: str, 
    title: str, 
    content: str, 
    tags: list, 
    main_keyword: str, 
    char_count: str, 
    products: str, 
    issues: list
) -> dict:
    """
    Gemini API를 호출하여 지적된 SEO 및 가독성 수정 필요 항목(issues)을 완벽히 수정한 보정 원고를 반환받습니다.
    """
    if not api_key:
        return {"error": "API Key가 유효하지 않아 자동 수정(Auto-Fix)을 수행할 수 없습니다."}
        
    try:
        
        prompt = f"""
당신은 네이버 블로그 검색 노출 마스터이자 교정 편집자입니다.
제시된 블로그 원고에서 발견된 '수정 필요 지적 내역(issues)'들을 완전히 조율하여, 네이버 SEO와 가독성 100점 만점을 받도록 보정한 최종 완결본 원고를 재작성해 주세요.

[수정 필요 지적 내역 (Issues)]
{chr(10).join([f"- {issue}" for issue in issues])}

[오리지널 원고 데이터]
- 메인 키워드: {main_keyword}
- 소개 상품군: {products}
- 목표 글자 수: {char_count}
- 오리지널 제목: {title}
- 오리지널 본문:
{content}
- 오리지널 태그: {', '.join(tags)}

[교정 필수 조건]
1. [지적 내역 우선 보완]: 지적된 모든 결함 사항(예: 키워드 누락 보완, 본문 키워드 도배 시 축소 조절, 소제목 추가, 문단 강제 줄바꿈 및 분할 등)을 완벽하게 교정하세요.
2. [문단 포맷팅]: **한 문단은 무조건 2~4문장 이내**로 대단히 짧게 마무리 짓고 다음 문단과의 사이에 엔터(줄바꿈)를 확실하게 주입해 모바일 가독성을 극대화하세요.
3. [링크 원칙 유지]: 본문에 박혀 있는 쇼커 링크(👉 형태)는 건드리지 말고 그 전후의 자연스러운 흐름을 고치거나 누락된 키워드를 삽입하는 방식으로 교정하세요.
4. [과장 광고 및 의학 단정 금지]: 수정 시 법적 문제가 되는 단어(완치, 치료 등)가 들어가거나 제품 강매 표현이 절대 부활하지 않도록 하세요.

[출력 형식]
반드시 다음의 JSON 형식으로만 응답해야 합니다. 다른 부연 설명이나 인사말은 일절 금지입니다.

{{
  "fixed_title": "완벽히 교정되어 메인 키워드가 자연스럽게 들어간 아름다운 최종 블로그 제목",
  "fixed_content": "수정 지침 및 모바일 2~4문장 문단 엔터 쪼개기 규칙을 완벽히 지켜 다시 쓴 최종 포스팅 본문 (줄바꿈 공백 개행을 자주 반영할 것)",
  "fixed_tags": ["교정 완료되어 5~10개 수량에 맞춰 재배열한 태그 목록"]
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
        return data
        
    except Exception as e:
        print(f"Auto-Fix 중 시스템 에러: {e}")
        return {"error": f"자동 교정 수행 중 에러 발생: {str(e)}"}
