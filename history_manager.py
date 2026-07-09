import json
import os
from datetime import datetime

HISTORY_FILE = "posts_history.json"

def load_history() -> list:
    """
    로컬 JSON 저장소에서 포스팅 작성 히스토리 리스트를 불러옵니다.
    """
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[History] 로드 실패: {e}")
        return []

def save_history(history: list) -> bool:
    """
    포스팅 히스토리 리스트를 로컬 JSON 파일에 안전하게 저장합니다.
    """
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[History] 저장 실패: {e}")
        return False

def add_or_update_post(post_id: str, post_data: dict) -> list:
    """
    특정 ID를 지닌 포스팅 정보를 업데이트하거나, 존재하지 않는 경우 신규 등록합니다.
    
    Args:
        post_id (str): 포스트 유니크 식별자 (신규 생성 시 None 또는 빈값 제공)
        post_data (dict): 저장/갱신할 포스트 필드 정보
        
    Returns:
        list: 갱신 완료된 히스토리 전체 리스트
    """
    history = load_history()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not post_id:
        # 신규 포스팅 등록
        post_id = f"post_{int(datetime.now().timestamp())}"
        new_entry = {
            "id": post_id,
            "created_at": now_str,
            "main_keyword": post_data.get("main_keyword", ""),
            "post_type": post_data.get("post_type", ""),
            "targets": post_data.get("targets", []),
            "products": post_data.get("products", ""),
            "links": post_data.get("links", []),
            "title": post_data.get("title", ""),
            "content": post_data.get("content", ""),
            "tags": post_data.get("tags", []),
            "seo_score": post_data.get("seo_score", 0),
            "ad_risk": post_data.get("ad_risk", "보통"),
            "naver_input_done": post_data.get("naver_input_done", False),
            "temp_save_done": post_data.get("temp_save_done", False),
            "publish_done": post_data.get("publish_done", False),
            "error_log": post_data.get("error_log", ""),
            "post_status": post_data.get("post_status", "초안 생성 완료")
        }
        history.insert(0, new_entry) # 최신 순서가 가장 위로 가도록 맨 앞에 삽입
    else:
        # 기존 포스팅 찾아 업데이트
        found = False
        for entry in history:
            if entry["id"] == post_id:
                # 데이터 병합 및 덮어쓰기
                entry["main_keyword"] = post_data.get("main_keyword", entry["main_keyword"])
                entry["post_type"] = post_data.get("post_type", entry["post_type"])
                entry["targets"] = post_data.get("targets", entry["targets"])
                entry["products"] = post_data.get("products", entry["products"])
                entry["links"] = post_data.get("links", entry["links"])
                entry["title"] = post_data.get("title", entry["title"])
                entry["content"] = post_data.get("content", entry["content"])
                entry["tags"] = post_data.get("tags", entry["tags"])
                entry["seo_score"] = post_data.get("seo_score", entry.get("seo_score", 0))
                entry["ad_risk"] = post_data.get("ad_risk", entry.get("ad_risk", "보통"))
                entry["naver_input_done"] = post_data.get("naver_input_done", entry.get("naver_input_done", False))
                entry["temp_save_done"] = post_data.get("temp_save_done", entry.get("temp_save_done", False))
                entry["publish_done"] = post_data.get("publish_done", entry.get("publish_done", False))
                entry["error_log"] = post_data.get("error_log", entry.get("error_log", ""))
                entry["post_status"] = post_data.get("post_status", entry["post_status"])
                # 최종 수정 시간으로 갱신하지 않고 생성 시간 유지 또는 개별 필드로 관리
                entry["updated_at"] = now_str
                found = True
                break
        
        if not found:
            # 매칭 ID가 없으면 강제 신규 취급하여 새로 삽입
            post_data["id"] = post_id
            post_data["created_at"] = now_str
            history.insert(0, post_data)
            
    save_history(history)
    return history

def delete_post_by_id(post_id: str) -> list:
    """
    히스토리 저장소에서 특정 포스팅 이력을 완전히 삭제합니다.
    """
    history = load_history()
    history = [entry for entry in history if entry["id"] != post_id]
    save_history(history)
    return history

def get_post_by_id(post_id: str) -> dict:
    """
    지정된 식별자를 가진 포스팅 상세 데이터를 조회합니다.
    """
    history = load_history()
    for entry in history:
        if entry["id"] == post_id:
            return entry
    return None
