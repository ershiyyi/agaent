from crewai import Agent
from src.agents import create_agents


def test_creates_four_agents():
    agents = create_agents()
    assert len(agents) == 4
    names = [a.role for a in agents]
    assert "内容策略分析师" in names
    assert "爆款选题策划师" in names
    assert "短视频脚本写手" in names
    assert "内容质量审核员" in names


def test_agents_have_goals():
    agents = create_agents()
    for agent in agents:
        assert agent.goal, f"{agent.role} should have a goal"
        assert agent.backstory, f"{agent.role} should have a backstory"
