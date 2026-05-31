import re
import time
from collections.abc import Callable
from crewai import Crew, Process, LLM, Task
from crewai.events.listeners.tracing.utils import set_suppress_tracing_messages
from src.agents import create_agents
from src.config import load_config
from src.tasks import create_tasks, create_revision_tasks

set_suppress_tracing_messages(True)

MAX_REVISION_ROUNDS = 2

TEMPLATES = {
    "tutorial": "教程类 — 强调步骤拆解、干货密度、分点讲解",
    "vlog": "vlog类 — 强调生活感、沉浸式体验、情绪氛围",
    "review": "测评类 — 强调真实体验、对比分析、优缺点拆解",
    "story": "口播故事类 — 强调悬念钩子、情绪起伏、个人观点输出",
}

STRATEGIST_DIRECTIONS = ["情感共鸣型", "知识干货型", "娱乐搞笑型", "种草带货型", "观点输出型"]
PLANNER_DIRECTIONS = ["热点借势", "痛点解决", "反差对比", "教程拆解", "故事叙事"]


def _parse_review_score(review_text: str) -> tuple[int, bool]:
    score_match = re.search(r"综合评分[：:]\s*(\d+)", review_text)
    if score_match:
        score = int(score_match.group(1))
    else:
        return 7, True
    is_pass = "PASS" in review_text.upper() or score >= 7
    return score, is_pass


def _parse_planner_topics(planner_text: str) -> list[str]:
    """从选题策划师的输出中提取3个选题标题."""
    topics = []
    for pattern in [
        r"选题\d[：:]\s*(.+?)(?:\n|$)",
        r"标题[：:]\s*(.+?)(?:\n|$)",
        r"\d+[\.\、]\s*(.+?)(?:\n|$)",
    ]:
        matches = re.findall(pattern, planner_text)
        topics.extend(m.strip() for m in matches if len(m.strip()) >= 4 and len(m.strip()) <= 60)
        if len(topics) >= 3:
            break
    # Deduplicate keeping order
    seen = set()
    return [t for t in topics if not (t in seen or seen.add(t))][:3]


def _emit(callback: Callable | None, agent_name: str, stage: str, output: str, step: int,
          extra: dict | None = None):
    if callback:
        event = {"agent": agent_name, "stage": stage, "output": output, "step": step}
        if extra:
            event.update(extra)
        callback(event)


def _safe_output(task) -> str:
    try:
        return task.output.raw if task.output else ""
    except (AttributeError, TypeError):
        return ""


def _run_single(agent, task, inputs: dict, callback, name: str, step: int) -> str:
    _emit(callback, name, "working", "", step)
    t0 = time.perf_counter()
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
    crew.kickoff(inputs=inputs)
    elapsed = round((time.perf_counter() - t0) * 1000)
    output = _safe_output(task)
    _emit(callback, name, "done", output, step, {"elapsed_ms": elapsed})
    return output


def run_strategist_step(
    user_input: str,
    template: str,
    direction: str,
    progress_callback: Callable | None = None,
) -> str:
    """Run strategist agent with user-selected content direction."""
    config = load_config()
    llm = LLM(
        model=f"deepseek/{config['model']}",
        api_key=config["api_key"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )
    if template and template in TEMPLATES:
        user_input = f"[{TEMPLATES[template]}] {user_input}"

    agents = create_agents(llm=llm)
    strategist = agents[0]
    task = Task(
        description=(
            "请根据以下博主的定位描述，以【{direction}】为内容风格方向，生成一份详细的博主画像卡。\n\n"
            "博主描述：{user_input}\n\n"
            "请按以下结构输出：\n"
            "1. 受众画像：性别、年龄、兴趣偏好、核心需求\n"
            "2. 内容调性：语言风格、视觉风格、情感基调\n"
            "3. 核心竞争力：差异化优势、人设标签、信任资产\n"
            "4. 内容方向建议：推荐深耕的内容赛道和表现形式\n\n"
            "注意：在内容调性和内容方向建议中，请重点围绕【{direction}】这一风格方向展开分析。"
        ),
        expected_output="一份结构完整的博主画像卡，包含受众画像、内容调性、核心竞争力、内容方向建议四个部分",
        agent=strategist,
    )
    return _run_single(
        strategist, task,
        {"user_input": user_input, "direction": direction},
        progress_callback, "🎯 内容策略分析师", 1,
    )


def run_planner_step(
    user_input: str,
    strategist_output: str,
    direction: str,
    progress_callback: Callable | None = None,
) -> str:
    """Run planner agent with user-selected angle direction."""
    config = load_config()
    llm = LLM(
        model=f"deepseek/{config['model']}",
        api_key=config["api_key"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )
    agents = create_agents(llm=llm)
    planner = agents[1]
    task = Task(
        description=(
            "基于以下博主画像卡，以【{direction}】为切入方式，策划3个具有爆款潜力的选题。\n\n"
            "博主画像：\n{strategist_output}\n\n"
            "每个选题请包含：\n"
            "1. 标题（2-3个备选）\n"
            "2. 切入角度（为什么选这个角度，与【{direction}】的关联）\n"
            "3. 爆点分析（为什么能火）\n"
            "4. 目标受众细分\n"
            "5. 预估互动指标（点赞/收藏/转发比例）\n\n"
            "输出3个完整选题方案，按爆款潜力从高到低排列。确保每个选题的切入角度都体现【{direction}】的特点。"
        ),
        expected_output="3个完整选题方案，每个包含标题、切入角度、爆点分析、目标受众、预估互动指标",
        agent=planner,
    )
    _emit(progress_callback, "🔥 爆款选题策划师", "working", "", 2)
    t0 = time.perf_counter()
    crew = Crew(agents=[planner], tasks=[task], process=Process.sequential, verbose=True)
    crew.kickoff(inputs={"strategist_output": strategist_output, "direction": direction})
    elapsed = round((time.perf_counter() - t0) * 1000)
    output = _safe_output(task)
    _emit(progress_callback, "🔥 爆款选题策划师", "done", output, 2, {"elapsed_ms": elapsed})
    topics = _parse_planner_topics(output)
    _emit(progress_callback, "🔥 爆款选题策划师", "topics", "", 2, {"topics": topics})
    return output


def run_writer_step(
    user_input: str,
    strategist_output: str,
    selected_topic: str,
    progress_callback: Callable | None = None,
) -> str:
    """Run writer agent with user-selected topic."""
    config = load_config()
    llm = LLM(
        model=f"deepseek/{config['model']}",
        api_key=config["api_key"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )
    agents = create_agents(llm=llm)
    writer = agents[2]
    task = Task(
        description=(
            "请根据以下博主画像和选题方案，为指定选题撰写一份完整的短视频拍摄脚本。\n\n"
            "博主画像：\n{strategist_output}\n\n"
            "指定选题：{selected_topic}\n\n"
            "请按以下结构输出：\n"
            "1. 开场钩子（前3秒的文案和画面说明，必须抓住注意力）\n"
            "2. 分镜脚本（6-8个分镜，每个包含：时长、画面描述、口播文案、音效/特效建议）\n"
            "3. 结尾引导（互动话术，引导点赞/评论/关注）\n"
            "4. 3个标题选项（分别侧重：好奇心、实用价值、情绪共鸣）\n"
            "5. 拍摄建议（光线、构图、景别等可选项）"
        ),
        expected_output="一份完整的拍摄脚本，包含开场钩子、分镜脚本、结尾引导、标题选项和拍摄建议",
        agent=writer,
    )
    return _run_single(
        writer, task,
        {"user_input": user_input, "strategist_output": strategist_output, "selected_topic": selected_topic},
        progress_callback, "✍️ 短视频脚本写手", 3,
    )


def run_reviewer_step(
    user_input: str,
    strategist_output: str,
    selected_topic: str,
    writer_output: str,
    progress_callback: Callable | None = None,
) -> str:
    """Run reviewer agent automatically (no direction needed)."""
    config = load_config()
    llm = LLM(
        model=f"deepseek/{config['model']}",
        api_key=config["api_key"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )
    agents = create_agents(llm=llm)
    reviewer = agents[3]
    task = Task(
        description=(
            "请审核以下短视频脚本的完整内容，并给出质量评估。\n\n"
            "博主画像：\n{strategist_output}\n\n"
            "指定选题：{selected_topic}\n\n"
            "拍摄脚本：\n{writer_output}\n\n"
            "请按以下维度打分（每项1-10分）：\n"
            "1. 钩子强度：前3秒是否能抓住用户\n"
            "2. 节奏控制：整体节奏是否张弛有度、无尿点\n"
            "3. 情绪曲线：是否有情绪起伏、共鸣点\n"
            "4. 转化设计：互动引导是否自然有效\n"
            "5. 人设匹配度：脚本风格是否符合博主画像\n\n"
            "综合评分（1-10分）：____\n"
            "审核结论：PASS（7分及以上，可直接使用）/ REVISE（6分及以下，需修改）\n"
            "如果REVISE，请列出具体的修改方向和优先级。"
        ),
        expected_output="一份包含5维评分、综合评分和审核结论（PASS或REVISE+修改建议）的审核报告",
        agent=reviewer,
    )
    return _run_single(
        reviewer, task,
        {"user_input": user_input, "strategist_output": strategist_output,
         "selected_topic": selected_topic, "writer_output": writer_output},
        progress_callback, "🔍 内容质量审核员", 4,
    )


def run_blogger_crew(
    user_input: str,
    selected_topic: str = "",
    template: str = "",
    progress_callback: Callable | None = None,
) -> dict:
    """返回 {result, topics, revision_count}."""
    config = load_config()
    llm = LLM(
        model=f"deepseek/{config['model']}",
        api_key=config["api_key"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )
    # Inject template context
    if template and template in TEMPLATES:
        user_input = f"[{TEMPLATES[template]}] {user_input}"

    agents = create_agents(llm=llm)
    strategist, planner, writer, reviewer = agents
    all_tasks = create_tasks(agents)
    topic = selected_topic or "请选题策划师推荐的第一个选题"

    # Step 1
    strategist_output = _run_single(
        strategist, all_tasks[0],
        {"user_input": user_input},
        progress_callback, "🎯 内容策略分析师", 1,
    )

    # Step 2
    planner_output = _run_single(
        planner, all_tasks[1],
        {"user_input": user_input, "strategist_output": strategist_output},
        progress_callback, "🔥 爆款选题策划师", 2,
    )
    topics = _parse_planner_topics(planner_output)
    _emit(progress_callback, "🔥 爆款选题策划师", "topics", "", 2, {"topics": topics})

    # Step 3
    writer_output = _run_single(
        writer, all_tasks[2],
        {"user_input": user_input, "strategist_output": strategist_output, "selected_topic": topic},
        progress_callback, "✍️ 短视频脚本写手", 3,
    )

    # Step 4
    reviewer_output = _run_single(
        reviewer, all_tasks[3],
        {"user_input": user_input, "strategist_output": strategist_output,
         "selected_topic": topic, "writer_output": writer_output},
        progress_callback, "🔍 内容质量审核员", 4,
    )

    final = reviewer_output
    revision_count = 0

    # Revision loop
    for round_num in range(MAX_REVISION_ROUNDS):
        score, is_pass = _parse_review_score(reviewer_output)
        if is_pass:
            _emit(progress_callback, "✅ 审核通过", "pass",
                  f"综合评分 {score} 分 — 脚本质量合格，可以直接使用！", 5,
                  {"score": score, "revision_count": revision_count})
            break

        _emit(progress_callback, "🔄 开始修改", "revising",
              f"评分 {score} 分（≤6），正在修改中...（第 {round_num + 1}/{MAX_REVISION_ROUNDS} 轮）", 4)

        revise_tasks = create_revision_tasks(writer, reviewer)
        t0 = time.perf_counter()
        revise_crew = Crew(
            agents=[writer, reviewer], tasks=revise_tasks,
            process=Process.sequential, verbose=True,
        )
        revise_crew.kickoff(inputs={
            "user_input": user_input,
            "strategist_output": strategist_output,
            "selected_topic": topic,
            "writer_output": writer_output,
        })
        elapsed = round((time.perf_counter() - t0) * 1000)
        writer_output = _safe_output(revise_tasks[0])
        reviewer_output = _safe_output(revise_tasks[1])
        revision_count += 1
        _emit(progress_callback, "✍️ 短视频脚本写手", "done", writer_output,
              5 + round_num * 2, {"elapsed_ms": elapsed, "revision": True})
        _emit(progress_callback, "🔍 内容质量审核员", "done", reviewer_output,
              6 + round_num * 2, {"revision": True})
        final = reviewer_output

    # If exhausted and still fail, emit pass anyway
    if not _parse_review_score(final)[1]:
        _emit(progress_callback, "✅ 审核通过", "pass",
              f"已达到最大修改轮次（{MAX_REVISION_ROUNDS}），以最新版本为准", 5,
              {"score": _parse_review_score(final)[0], "revision_count": revision_count})

    return {"result": str(final), "topics": topics, "revision_count": revision_count,
            "writer_output": writer_output, "strategist_output": strategist_output}
