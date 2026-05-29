from unittest.mock import patch, MagicMock
from src.crew import run_blogger_crew


@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew.Crew")
def test_full_pipeline_with_pass(mock_crew_class, mock_llm_class, mock_load_config, mock_create_agents, mock_create_tasks):
    """Reviewer says PASS on first attempt -- revision loop is never entered."""
    mock_load_config.return_value = {
        "api_key": "test-api-key",
        "model": "claude-sonnet-4-6",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

    def crew_factory(*args, **kwargs):
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if isinstance(tasks, list):
                for i, task in enumerate(tasks):
                    if i == 0:
                        task.output = MagicMock(raw="博主画像：美妆教程博主，受众18-25岁女性...")
                    elif i == 1:
                        task.output = MagicMock(raw="选题1：夏日护肤...\n选题2：秋季妆容...\n选题3：...")
                    elif i == 2:
                        task.output = MagicMock(raw="## 拍摄脚本\n分镜1：开场钩子...")
                    elif i == 3:
                        task.output = MagicMock(raw="综合评分：8分\n审核结论：PASS")
            return "完整脚本输出内容"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(
        user_input="美妆教程博主，粉丝18-25岁女性",
        selected_topic="夏日护肤",
    )

    # Verify pipeline completed and returned the expected output
    assert result == "完整脚本输出内容"

    # Verify ONLY one Crew was created (revision loop was never entered)
    assert mock_crew_class.call_count == 1

    # Verify the single Crew was created with 4 agents and 4 tasks
    first_call_kwargs = mock_crew_class.call_args_list[0][1]
    assert len(first_call_kwargs["agents"]) == 4
    assert len(first_call_kwargs["tasks"]) == 4


@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew.Crew")
def test_full_pipeline_needs_revision(mock_crew_class, mock_llm_class, mock_load_config, mock_create_agents, mock_create_tasks):
    """Reviewer says REVISE on first run, PASS on revision -- exactly 2 Crews."""
    mock_load_config.return_value = {
        "api_key": "test-api-key",
        "model": "claude-sonnet-4-6",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

    call_count = [0]

    def crew_factory(*args, **kwargs):
        call_count[0] += 1
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if call_count[0] == 1:
                # First Crew: 4 tasks, reviewer says REVISE (score 5)
                if isinstance(tasks, list):
                    for i, task in enumerate(tasks):
                        if i == 0:
                            task.output = MagicMock(raw="博主画像：美妆博主...")
                        elif i == 1:
                            task.output = MagicMock(raw="选题1：护肤...\n选题2：彩妆...\n选题3：...")
                        elif i == 2:
                            task.output = MagicMock(raw="## 初稿脚本\n分镜1：普通开场...")
                        elif i == 3:
                            task.output = MagicMock(
                                raw="综合评分：5分\n审核结论：REVISE\n修改建议：开场钩子太弱，缺乏吸引力"
                            )
            else:
                # Revision Crew: 2 tasks (writer + reviewer), reviewer says PASS
                if isinstance(tasks, list) and len(tasks) >= 2:
                    tasks[0].output = MagicMock(raw="## 修改后脚本\n分镜1：强力钩子开场...")
                    tasks[1].output = MagicMock(raw="综合评分：8分\n审核结论：PASS")
            return "流程完成"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(
        user_input="美妆博主",
        selected_topic="护肤",
    )

    # Verify pipeline completed
    assert result is not None
    assert result == "流程完成"

    # Verify EXACTLY two Crews were created (initial + one revision)
    assert call_count[0] == 2
    assert mock_crew_class.call_count == 2

    # Verify second Crew was revision-specific: 2 agents (writer + reviewer)
    second_call_kwargs = mock_crew_class.call_args_list[1][1]
    assert len(second_call_kwargs["agents"]) == 2
    assert len(second_call_kwargs["tasks"]) == 2


@patch("src.crew.create_tasks")
@patch("src.crew.create_agents")
@patch("src.crew.load_config")
@patch("src.crew.LLM")
@patch("src.crew.Crew")
def test_pipeline_exhausted_revisions(mock_crew_class, mock_llm_class, mock_load_config, mock_create_agents, mock_create_tasks):
    """When reviewer ALWAYS says REVISE, function returns after MAX_REVISION_ROUNDS (2)
    without infinite looping."""
    mock_load_config.return_value = {
        "api_key": "test-api-key",
        "model": "claude-sonnet-4-6",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    mock_llm_class.return_value = MagicMock()
    mock_create_agents.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_create_tasks.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

    call_count = [0]

    def crew_factory(*args, **kwargs):
        call_count[0] += 1
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if isinstance(tasks, list):
                num_tasks = len(tasks)
                for i, task in enumerate(tasks):
                    if num_tasks == 4:
                        # First Crew: strategist(0), planner(1), writer(2), reviewer(3)
                        if i == 0:
                            task.output = MagicMock(raw=f"博主画像：测试... (第{call_count[0]}轮)")
                        elif i == 1:
                            task.output = MagicMock(raw=f"选题：测试... (第{call_count[0]}轮)")
                        elif i == 2:
                            task.output = MagicMock(raw=f"## 脚本第{call_count[0]}版...")
                        elif i == 3:
                            task.output = MagicMock(
                                raw=f"综合评分：5分\n审核结论：REVISE\n修改建议：仍需改进 (第{call_count[0]}轮)"
                            )
                    elif num_tasks == 2:
                        # Revision Crew: writer(0), reviewer(1)
                        if i == 0:
                            task.output = MagicMock(raw=f"## 脚本第{call_count[0]}版...")
                        elif i == 1:
                            task.output = MagicMock(
                                raw=f"综合评分：5分\n审核结论：REVISE\n修改建议：仍需改进 (第{call_count[0]}轮)"
                            )
            return f"流程完成第{call_count[0]}轮"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(user_input="测试博主", selected_topic="测试选题")

    # Verify function returned without error (no infinite loop)
    assert result is not None
    assert result == "流程完成第3轮"

    # Verify exactly 3 Crews: initial + 2 revisions (MAX_REVISION_ROUNDS)
    assert call_count[0] == 3
    assert mock_crew_class.call_count == 3

    # Verify every revision Crew had exactly 2 tasks (writer + reviewer)
    for idx in [1, 2]:
        revision_kwargs = mock_crew_class.call_args_list[idx][1]
        assert len(revision_kwargs["agents"]) == 2, (
            f"Revision Crew #{idx} should have 2 agents"
        )
        assert len(revision_kwargs["tasks"]) == 2, (
            f"Revision Crew #{idx} should have 2 tasks"
        )
