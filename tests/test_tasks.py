from src.tasks import create_tasks, create_revision_tasks
from src.agents import create_agents


def test_creates_four_tasks():
    agents = create_agents()
    tasks = create_tasks(agents)
    assert len(tasks) == 4


def test_tasks_bound_to_correct_agents():
    agents = create_agents()
    tasks = create_tasks(agents)
    assert tasks[0].agent.role == "内容策略分析师"
    assert tasks[1].agent.role == "爆款选题策划师"
    assert tasks[2].agent.role == "短视频脚本写手"
    assert tasks[3].agent.role == "内容质量审核员"


def test_strategist_task_contains_user_input_placeholder():
    agents = create_agents()
    tasks = create_tasks(agents)
    assert "{user_input}" in tasks[0].description


def test_planner_uses_strategist_template():
    agents = create_agents()
    tasks = create_tasks(agents)
    assert "{strategist_output}" in tasks[1].description


def test_writer_uses_templates():
    agents = create_agents()
    tasks = create_tasks(agents)
    assert "{strategist_output}" in tasks[2].description
    assert "{selected_topic}" in tasks[2].description


def test_reviewer_uses_templates():
    agents = create_agents()
    tasks = create_tasks(agents)
    assert "{strategist_output}" in tasks[3].description
    assert "{selected_topic}" in tasks[3].description
    assert "{writer_output}" in tasks[3].description


def test_creates_two_revision_tasks():
    agents = create_agents()
    _, __, writer, reviewer = agents
    tasks = create_revision_tasks(writer, reviewer)
    assert len(tasks) == 2
    assert tasks[0].agent.role == "短视频脚本写手"
    assert tasks[1].agent.role == "内容质量审核员"


def test_revision_writer_accepts_templates():
    agents = create_agents()
    _, __, writer, reviewer = agents
    tasks = create_revision_tasks(writer, reviewer)
    assert "{strategist_output}" in tasks[0].description
    assert "{selected_topic}" in tasks[0].description
    assert "{writer_output}" in tasks[0].description
