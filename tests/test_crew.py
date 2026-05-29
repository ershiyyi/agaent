from unittest.mock import patch, MagicMock
from src.crew import run_blogger_crew, _parse_review_score


def test_parse_review_score_pass():
    review = """
    钩子强度：8
    节奏控制：7
    情绪曲线：8
    转化设计：7
    人设匹配度：8
    综合评分：8分
    审核结论：PASS
    """
    score, is_pass = _parse_review_score(review)
    assert score == 8
    assert is_pass is True


def test_parse_review_score_revise():
    review = """
    综合评分：5分
    审核结论：REVISE
    """
    score, is_pass = _parse_review_score(review)
    assert score == 5
    assert is_pass is False


def test_parse_review_score_default():
    score, is_pass = _parse_review_score("无明确评分")
    assert score == 7  # default pass
    assert is_pass is True


@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew._parse_review_score", return_value=(8, True))
@patch("src.crew.Crew")
def test_run_blogger_crew_calls_kickoff(mock_crew_class, mock_parse, mock_llm_class, mock_load_config, mock_create_agents, mock_create_tasks):
    mock_load_config.return_value = {
        "api_key": "test-api-key",
        "model": "claude-sonnet-4-6",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = "最终脚本输出"
    mock_crew_class.return_value = mock_crew

    result = run_blogger_crew(user_input="美妆博主", selected_topic="护肤教程")
    assert result == "最终脚本输出"
    mock_crew.kickoff.assert_called_once()


@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew._parse_review_score", return_value=(5, False))
@patch("src.crew.Crew")
def test_revision_loop_runs_twice_when_needed(mock_crew_class, mock_parse, mock_llm_class, mock_load_config, mock_create_agents, mock_create_tasks):
    """When reviewer keeps saying REVISE, both revision rounds are attempted."""
    mock_load_config.return_value = {
        "api_key": "test-api-key",
        "model": "claude-sonnet-4-6",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

    mock_crew = MagicMock()
    # First run - strategist + planner + writer + reviewer (score 5)
    # First revision - writer + reviewer (score 5)
    # Second revision - writer + reviewer (score 5)
    mock_crew.kickoff.side_effect = ["result1", "result2", "result3"]
    mock_crew_class.return_value = mock_crew

    result = run_blogger_crew(user_input="test", selected_topic="test")

    assert mock_crew.kickoff.call_count == 3  # initial + 2 revisions
