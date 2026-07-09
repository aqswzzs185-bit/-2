import json
import os

STATE_FILE = "current_workspace_state.json"

def save_workspace_state(state_dict: dict) -> bool:
    """
    현재 작업 중인 세션 정보(제목, 본문, 상태값 등)를 JSON 파일에 영구 저장합니다.
    """
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[State] 로컬 상태 저장 실패: {e}")
        return False

def load_workspace_state() -> dict:
    """
    로컬 파일에서 중단되었던 이전 작업 세션 상태를 복원 로드합니다.
    """
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[State] 로컬 상태 로드 실패: {e}")
        return {}

def reset_workspace_state() -> bool:
    """
    새로운 글 작성을 위해 기존 로컬 임시 작업 상태 파일을 완전히 제거합니다.
    """
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            return True
        except Exception as e:
            print(f"[State] 로컬 상태 파일 제거 실패: {e}")
            return False
    return True
