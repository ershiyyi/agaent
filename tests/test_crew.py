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


@patch("src.crew.Crew")
def test_run_blogger_crew_calls_kickoff(mock_crew_class):
    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = "最终脚本输出"
    mock_crew_class.return_value = mock_crew

    result = run_blogger_crew(user_input="美妆博主", selected_topic="护肤教程")
    assert result == "最终脚本输出"
    mock_crew.kickoff.assert_called_once()
