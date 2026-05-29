import re
from crewai import Crew, Process
from src.agents import create_agents
from src.tasks import create_tasks

MAX_REVISION_ROUNDS = 2


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
    agents = create_agents()
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

    # 检查是否需要修改
    for round_num in range(MAX_REVISION_ROUNDS):
        try:
            reviewer_output = tasks[3].output.raw if tasks[3].output else ""
        except Exception:
            reviewer_output = str(result)

        score, is_pass = _parse_review_score(reviewer_output)
        if is_pass:
            break

        if round_num < MAX_REVISION_ROUNDS - 1:
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
            result = revise_crew.kickoff(inputs={
                "user_input": user_input,
                "strategist_output": tasks[0].output.raw if tasks[0].output else "",
                "selected_topic": selected_topic,
                "writer_output": "",
            })

    return str(result)
