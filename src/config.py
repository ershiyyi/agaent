import os
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "model": "claude-sonnet-4-6",
    "temperature": 0.7,
    "max_tokens": 2000,
}


def load_config():
    return {
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": LLM_CONFIG["model"],
        "temperature": LLM_CONFIG["temperature"],
        "max_tokens": LLM_CONFIG["max_tokens"],
    }
