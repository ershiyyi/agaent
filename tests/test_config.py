import os
from unittest.mock import patch
from src.config import load_config, LLM_CONFIG


def test_load_config_with_env_var():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        config = load_config()
        assert config["api_key"] == "sk-ant-test"


def test_llm_config_has_model():
    assert "model" in LLM_CONFIG
    assert LLM_CONFIG["model"].startswith("claude")


def test_load_config_missing_key():
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
        assert config["api_key"] == ""


def test_load_config_includes_llm_fields():
    config = load_config()
    assert config["model"] == LLM_CONFIG["model"]
    assert config["temperature"] == LLM_CONFIG["temperature"]
    assert config["max_tokens"] == LLM_CONFIG["max_tokens"]
