from unittest.mock import patch, MagicMock
from src.crew import run_blogger_crew


@patch("src.crew.create_revision_tasks")
@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew.Crew")
def test_full_pipeline_with_pass(mock_crew_class, mock_llm_class, mock_load_config,
                                  mock_create_agents, mock_create_tasks, mock_create_revision):
    mock_load_config.return_value = {
        "api_key": "test-key", "model": "deepseek-chat",
        "temperature": 0.7, "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

    crew_call = [0]

    def crew_factory(*args, **kwargs):
        crew_call[0] += 1
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if isinstance(tasks, list) and len(tasks) > 0:
                out = MagicMock()
                if crew_call[0] == 1:
                    out.raw = "博主画像：美妆教程博主..."
                elif crew_call[0] == 2:
                    out.raw = "选题1：夏日护肤\n选题2：秋季妆容\n选题3：..."
                elif crew_call[0] == 3:
                    out.raw = "## 拍摄脚本\n分镜1：开场钩子..."
                elif crew_call[0] == 4:
                    out.raw = "综合评分：8分\n审核结论：PASS"
                tasks[0].output = out
            return "流程完成"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(user_input="美妆教程博主", selected_topic="夏日护肤")

    assert result["result"] is not None
    assert result["revision_count"] == 0
    assert mock_crew_class.call_count == 4


@patch("src.crew.create_revision_tasks")
@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew.Crew")
def test_full_pipeline_needs_revision(mock_crew_class, mock_llm_class, mock_load_config,
                                       mock_create_agents, mock_create_tasks, mock_create_revision):
    mock_load_config.return_value = {
        "api_key": "test-key", "model": "deepseek-chat",
        "temperature": 0.7, "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_revision.return_value = [MagicMock(), MagicMock()]

    crew_call = [0]

    def crew_factory(*args, **kwargs):
        crew_call[0] += 1
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if isinstance(tasks, list) and len(tasks) > 0:
                if crew_call[0] == 4:
                    out = MagicMock()
                    out.raw = "综合评分：5分\n审核结论：REVISE\n修改建议：开场钩子太弱"
                    tasks[0].output = out
                elif crew_call[0] == 5:
                    out0 = MagicMock(); out0.raw = "修改后的脚本"
                    out1 = MagicMock(); out1.raw = "综合评分：8分\n审核结论：PASS"
                    tasks[0].output = out0; tasks[1].output = out1
                else:
                    out = MagicMock(); out.raw = "output"
                    tasks[0].output = out
            return "流程完成"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(user_input="美妆博主", selected_topic="护肤")
    assert result["result"] is not None
    assert crew_call[0] == 5


@patch("src.crew.create_revision_tasks")
@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew.Crew")
def test_pipeline_exhausted_revisions(mock_crew_class, mock_llm_class, mock_load_config,
                                       mock_create_agents, mock_create_tasks, mock_create_revision):
    mock_load_config.return_value = {
        "api_key": "test-key", "model": "deepseek-chat",
        "temperature": 0.7, "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_revision.return_value = [MagicMock(), MagicMock()]

    crew_call = [0]

    def crew_factory(*args, **kwargs):
        crew_call[0] += 1
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if isinstance(tasks, list) and len(tasks) > 0:
                if crew_call[0] >= 5:
                    out0 = MagicMock(); out0.raw = "修改后的脚本"
                    out1 = MagicMock(); out1.raw = "综合评分：5分\n审核结论：REVISE"
                    tasks[0].output = out0; tasks[1].output = out1
                else:
                    out = MagicMock()
                    out.raw = f"第{crew_call[0]}步输出" if crew_call[0] < 4 else "综合评分：5分\n审核结论：REVISE"
                    tasks[0].output = out
            return f"流程完成第{crew_call[0]}轮"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(user_input="测试博主", selected_topic="测试选题")
    assert result["result"] is not None
    assert result["revision_count"] == 2
    assert crew_call[0] == 6
