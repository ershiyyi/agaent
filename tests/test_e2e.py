from unittest.mock import patch, MagicMock
from src.crew import run_blogger_crew


@patch("src.crew.Crew")
def test_full_pipeline_with_pass(mock_crew_class):
    """端到端测试：审核一次通过的情况."""
    mock_task_outputs = [
        MagicMock(raw="博主画像：美妆教程博主..."),                      # strategist
        MagicMock(raw="选题1：夏日护肤...\n选题2：...\n选题3：..."),    # planner
        MagicMock(raw="## 拍摄脚本\n分镜1..."),                         # writer
        MagicMock(raw="综合评分：8分\n审核结论：PASS"),                  # reviewer
    ]

    def crew_factory(*args, **kwargs):
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if isinstance(tasks, list):
                for i, task in enumerate(tasks):
                    if i < len(mock_task_outputs):
                        task.output = mock_task_outputs[i]
            return "流程完成"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(
        user_input="美妆教程博主，粉丝18-25岁女性",
        selected_topic="夏日护肤",
    )

    assert result is not None


@patch("src.crew.Crew")
def test_full_pipeline_needs_revision(mock_crew_class):
    """端到端测试：需要修改一轮后通过的情况."""
    crew_call_count = [0]

    def crew_factory(*args, **kwargs):
        crew_call_count[0] += 1
        mock_crew = MagicMock()
        tasks = kwargs.get("tasks", [])

        def kickoff_side_effect(*a, **kw):
            if crew_call_count[0] == 1:
                # First run: all 4 tasks, reviewer says REVISE
                if isinstance(tasks, list) and len(tasks) >= 4:
                    tasks[0].output = MagicMock(raw="博主画像：...")
                    tasks[1].output = MagicMock(raw="选题：...")
                    tasks[2].output = MagicMock(raw="## 初稿脚本...")
                    tasks[3].output = MagicMock(
                        raw="综合评分：5分\n审核结论：REVISE\n修改建议：开场钩子太弱"
                    )
            else:
                # Revision run: 2 tasks (writer + reviewer), reviewer says PASS
                if isinstance(tasks, list) and len(tasks) >= 2:
                    tasks[0].output = MagicMock(raw="## 修改后脚本...")
                    tasks[1].output = MagicMock(raw="综合评分：8分\n审核结论：PASS")
            return "流程完成"

        mock_crew.kickoff.side_effect = kickoff_side_effect
        return mock_crew

    mock_crew_class.side_effect = crew_factory

    result = run_blogger_crew(
        user_input="美妆博主",
        selected_topic="护肤",
    )

    assert result is not None
    # kickoff should be called at least once (first run + at least one revision)
    assert crew_call_count[0] >= 2
