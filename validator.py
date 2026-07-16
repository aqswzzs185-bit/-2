import json
import re
from generator import call_gemini_rest_api

# 로컬 스캐닝용 금지/위험 단어 목록
EXAGGERATION_WORDS = ["무조건", "최고", "완벽", "필수 구매", "효과 보장", "무조건 필요", "절대적", "가장 뛰어난", "100% 효과"]
MEDICAL_WORDS = ["치료", "완치", "통증이 사라진다", "병이 낫는다", "관절염 해결", "질병 극복", "특효약", "의학적 검증"]

def local_keyword_scan(text: str) -> tuple:
    """
    로컬 검색 방식으로 텍스트 내 과장 표현 및 의학 단정 키워드 출현 횟수를 계측합니다.
    """
    exag_count = 0
    med_count = 0
    
    for word in EXAGGERATION_WORDS:
        exag_count += len(re.findall(re.escape(word), text))
        
    for word in MEDICAL_WORDS:
        med_count += len(re.findall(re.escape(word), text))
        
    return exag_count, med_count

def run_content_check(api_key: str, title: str, content: str, tags: list) -> dict:
    """
    Gemini API 및 로컬 룰을 하이브리드로 사용하여 블로그 원고의 품질과 안전 심사를 진행합니다.
    
    Args:
        api_key (str): Gemini API 키
        title (str): 최종 블로그 제목
        content (str): 최종 블로그 본문
        tags (list): 해시태그 목록
        
    Returns:
        dict: 검수 결과 정보가 담긴 사전
    """
    # 1. 로컬 1차 스캐닝
    local_exag, local_med = local_keyword_scan(content)
    
    # 2. AI 정밀 다차원 심사 (Gemini API 호출)
    if not api_key:
        return {
            "ad_risk": "보통",
            "exaggeration_count": local_exag,
            "medical_assertion_count": local_med,
            "recommended_edits": [{"original_sentence": "API Key 없음", "alternative_sentence": "설정에서 API Key를 보완해 주시기 바랍니다.", "reason": "품질 검수를 진행할 수 없습니다."}],
            "is_publishable": False,
            "message": "Gemini API 키가 제공되지 않아 AI 정밀 심사를 건너뛰고 로컬 단어 분석만 수행했습니다."
        }
        
    try:
        
        full_document = f"제목: {title}\n\n본문:\n{content}\n\n해시태그: {', '.join(tags)}"
        
        prompt = f"""
당신은 네이버 블로그 콘텐츠 가이드라인 및 의료법/광고법 준수를 검토하는 최고 준법 감시관(Compliance Officer)입니다.
아래의 블로그 포스팅 원고를 읽고 다음 10가지 검수 조건에 의거하여 냉철하게 포스팅의 안전도와 가독성을 정밀 검수해 주세요.

[10대 검수 조건]
1. “무조건”, “최고”, “완벽”, “필수 구매” 같은 광고성 과장 표현 유무
2. “치료”, “완치”, “통증이 사라진다”, “병이 낫는다” 등 의학적으로 효능을 단정 짓는 소지가 있는지 확인
3. 직접적인 구매나 주문을 지나치게 강요/압박하는 어투 유무
4. 본문 내 삽입된 쇼커 링크(👉 형태)가 과도하게 난무하는지 확인 (2회 초과 시 위험)
5. 같은 링크에 대한 문구가 글 속에서 토씨 하나 안 틀리고 중복되는지 여부
6. 문장 종결 어미나 구조가 기계적으로 반복되어 사람이 쓴 글 느낌을 깨뜨리는지 확인
7. 글의 분위기가 유익한 생활 정보 공유보다 온통 노골적인 제품 광고로만 도배되었는지 비율 진단
8. 낙상이나 질병 위험을 묘사할 때, 부모님에 대한 불안과 공포심을 가스라이팅 수준으로 과도하게 자극하는지 확인
9. 고령자나 부모님을 비하하거나, 너무 무력하고 슬프게만 묘사하여 어르신 독자에게 불쾌감을 주는지 확인
10. 네이버 블로그 이웃 및 일반 자녀 독자가 정독하기에 전반적인 문체와 문맥이 매끄러운지 확인

[포스팅 원고 데이터]
{full_document}

[출력 형식]
반드시 아래의 JSON 구조로만 응답해야 합니다. 마크다운 JSON 블록(```json ... ```)으로 묶어도 좋으나 다른 말은 절대로 덧붙이지 마십시오.

{{
  "ad_risk": "낮음 또는 보통 또는 높음 (광고성 위험도 종합 평가)",
  "exaggeration_count": {local_exag} (위 포스팅 내 과장 단어 및 표현의 총 개수),
  "medical_assertion_count": {local_med} (의학적 단정 표현의 총 개수),
  "recommended_edits": [
    {{
      "original_sentence": "문제가 발견되어 수정이 강하게 필요한 문장 (없을 시 이 리스트는 비워두십시오)",
      "alternative_sentence": "해당 규칙을 완벽하게 우회하면서도 자연스럽고 따뜻한 대체 문장 제안",
      "reason": "해당 문장이 지적된 이유 (예: 2번 의학적 단정 우려 등)"
    }}
  ],
  "is_publishable": true 또는 false (모든 검수 규칙을 충족하고 실 배포해도 안전하면 true, 과장 광고나 법적 문제가 너무 심각하면 false)
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
        
        # 만약 로컬 분석 결과 수치보다 AI 분석 수치가 비정상적으로 낮으면 로컬 수치를 강제 덮어쓰기하여 크로스체크 강화
        data["exaggeration_count"] = max(data.get("exaggeration_count", 0), local_exag)
        data["medical_assertion_count"] = max(data.get("medical_assertion_count", 0), local_med)
        
        return data
        
    except json.JSONDecodeError as je:
        print(f"JSON 파싱 실패: {je}")
        return {
            "ad_risk": "보통",
            "exaggeration_count": local_exag,
            "medical_assertion_count": local_med,
            "recommended_edits": [],
            "is_publishable": True if (local_exag + local_med == 0) else False,
            "error": "AI 검증 응답을 파싱할 수 없어 로컬 기본 룰로 최종 대체 판정했습니다."
        }
    except Exception as e:
        print(f"검수 에이전트 구동 에러: {e}")
        return {
            "ad_risk": "보통",
            "exaggeration_count": local_exag,
            "medical_assertion_count": local_med,
            "recommended_edits": [],
            "is_publishable": True if (local_exag + local_med == 0) else False,
            "error": f"검수 중 시스템 오류 발생: {str(e)}"
        }
