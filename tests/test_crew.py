from unittest.mock import patch, MagicMock
from src.crew import run_blogger_crew, _parse_review_score, _parse_planner_topics


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
    assert score == 7
    assert is_pass is True


def test_parse_planner_topics_extracts_titles():
    text = """
    选题1：夏日护肤秘籍大公开
    选题2：秋季妆容搭配指南
    选题3：平价好物推荐清单
    """
    topics = _parse_planner_topics(text)
    assert len(topics) == 3
    assert "夏日护肤秘籍大公开" in topics


@patch("src.crew.create_revision_tasks")
@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew._parse_planner_topics", return_value=[])
@patch("src.crew._parse_review_score", return_value=(8, True))
@patch("src.crew.Crew")
def test_run_blogger_crew_with_pass(
    mock_crew_class, mock_parse, mock_parse_topics, mock_llm_class,
    mock_load_config, mock_create_agents, mock_create_tasks, mock_create_revision
):
    mock_load_config.return_value = {
        "api_key": "test-key", "model": "deepseek-chat",
        "temperature": 0.7, "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = "task result"
    mock_crew_class.return_value = mock_crew

    result = run_blogger_crew(user_input="美妆博主", selected_topic="护肤教程")

    assert result["result"] is not None
    assert "topics" in result
    assert mock_crew_class.call_count == 4


@patch("src.crew.create_revision_tasks")
@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew._parse_planner_topics", return_value=[])
@patch("src.crew._parse_review_score", return_value=(5, False))
@patch("src.crew.Crew")
def test_revision_loop_runs_twice_when_needed(
    mock_crew_class, mock_parse, mock_parse_topics, mock_llm_class,
    mock_load_config, mock_create_agents, mock_create_tasks, mock_create_revision
):
    mock_load_config.return_value = {
        "api_key": "test-key", "model": "deepseek-chat",
        "temperature": 0.7, "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_revision.return_value = [MagicMock(), MagicMock()]

    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = "result"
    mock_crew_class.return_value = mock_crew

    result = run_blogger_crew(user_input="test", selected_topic="test")
    # 4 initial + 2 revision crews
    assert mock_crew_class.call_count == 6
    assert result["revision_count"] == 2
    assert isinstance(result["result"], str)
