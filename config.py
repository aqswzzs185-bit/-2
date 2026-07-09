import os
import json

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "GEMINI_API_KEY": "",
    "NAVER_ID": "",
    "CHROME_PROFILE_DIR": "./naver_chrome_profile",
    "DEFAULT_TONE": "자녀가 부모님의 건강과 안전을 진심으로 걱정하고 배려하는 따뜻하고 정중한 어조"
}

def load_config():
    """설정 파일을 읽어옵니다. 파일이 없으면 기본 설정을 생성합니다."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # 기본 키가 누락되었을 경우를 대비해 병합
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception as e:
        print(f"설정 로드 오류: {e}")
        return DEFAULT_CONFIG

def save_config(config_data):
    """설정 파일을 저장합니다."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"설정 저장 오류: {e}")
        return False
