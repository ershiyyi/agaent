import re
from crewai import Crew, Process, LLM
from src.agents import create_agents
from src.config import load_config
from src.tasks import create_tasks

MAX_REVISION_ROUNDS = 2  # 最多进行2轮修改（round_num 0 和 1 各触发一次）


def _parse_review_score(review_text: str) -> tuple[int, bool]:
    """从审核文本中提取评分和PASS/REVISE结论."""
    score_match = re.search(r"综合评分[：:]\s*(\d+)", review_text)
    if score_match:
        score = int(score_match.group(1))
    else:
        return 7, True  # 无法解析时默认通过

    is_pass = "PASS" in review_text.upper() or score >= 7
    return score, is_pass


def run_blogger_crew(
    user_input: str,
    selected_topic: str = "",
) -> str:
    """运行博主创作多Agent流程，返回最终结果."""
    config = load_config()

    llm = LLM(
        model=f"anthropic/{config['model']}",
        api_key=config["api_key"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

    agents = create_agents(llm=llm)
    tasks = create_tasks(agents)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    # 第一轮运行
    result = crew.kickoff(inputs={
        "user_input": user_input,
        "selected_topic": selected_topic or "请选题策划师推荐的第一个选题",
    })

    # 读取初始审核结果（Bug 4 fix: 使用具体异常类型）
    try:
        reviewer_output = tasks[3].output.raw if tasks[3].output else ""
    except (AttributeError, TypeError):
        reviewer_output = str(result)

    # 记录最新的Writer输出，用于修改轮次
    try:
        current_writer_output = tasks[2].output.raw if tasks[2].output else ""
    except (AttributeError, TypeError):
        current_writer_output = ""

    # 检查是否需要修改
    for round_num in range(MAX_REVISION_ROUNDS):
        score, is_pass = _parse_review_score(reviewer_output)
        if is_pass:
            break

        # Bug 1 fix: 使用 < MAX_REVISION_ROUNDS 而不是 < MAX_REVISION_ROUNDS - 1
        # 这样 round_num 0 和 1 都可以触发修改轮次
        if round_num < MAX_REVISION_ROUNDS:
            # 重建Writer和Reviewer的crew来修改
            _, __, writer, reviewer = agents
            revise_tasks = create_tasks(agents)
            revise_tasks = [revise_tasks[2], revise_tasks[3]]  # only writer + reviewer

            revise_crew = Crew(
                agents=[writer, reviewer],
                tasks=revise_tasks,
                process=Process.sequential,
                verbose=True,
            )
            # Bug 3 fix: 传入最新的Writer输出，而不是空字符串
            result = revise_crew.kickoff(inputs={
                "user_input": user_input,
                "strategist_output": tasks[0].output.raw if tasks[0].output else "",
                "selected_topic": selected_topic,
                "writer_output": current_writer_output,
            })

            # Bug 2 fix: 从修改任务的审阅员输出读取结果，用于下一轮的PASS/REVISE判断
            try:
                reviewer_output = revise_tasks[1].output.raw if revise_tasks[1].output else ""
            except (AttributeError, TypeError):
                reviewer_output = str(result)

            # 更新Writer输出，供下一轮修改使用
            try:
                current_writer_output = revise_tasks[0].output.raw if revise_tasks[0].output else ""
            except (AttributeError, TypeError):
                current_writer_output = ""

    return str(result)
