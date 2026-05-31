from crewai import Agent, Task


def create_tasks(agents: list[Agent]) -> list[Task]:
    strategist, planner, writer, reviewer = agents

    task_strategist = Task(
        description=(
            "请根据以下博主的定位描述，生成一份详细的博主画像卡。\n\n"
            "博主描述：{user_input}\n\n"
            "请按以下结构输出：\n"
            "1. 受众画像：性别、年龄、兴趣偏好、核心需求\n"
            "2. 内容调性：语言风格、视觉风格、情感基调\n"
            "3. 核心竞争力：差异化优势、人设标签、信任资产\n"
            "4. 内容方向建议：推荐深耕的内容赛道和表现形式"
        ),
        expected_output="一份结构完整的博主画像卡，包含受众画像、内容调性、核心竞争力、内容方向建议四个部分",
        agent=strategist,
    )

    task_planner = Task(
        description=(
            "基于以下博主画像卡，策划3个具有爆款潜力的选题。\n\n"
            "博主画像：\n{strategist_output}\n\n"
            "每个选题请包含：\n"
            "1. 标题（2-3个备选）\n"
            "2. 切入角度（为什么选这个角度）\n"
            "3. 爆点分析（为什么能火）\n"
            "4. 目标受众细分\n"
            "5. 预估互动指标（点赞/收藏/转发比例）\n\n"
            "输出3个完整选题方案，按爆款潜力从高到低排列。"
        ),
        expected_output="3个完整选题方案，每个包含标题、切入角度、爆点分析、目标受众、预估互动指标",
        agent=planner,
    )

    task_writer = Task(
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

    task_reviewer = Task(
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

    return [task_strategist, task_planner, task_writer, task_reviewer]


def create_revision_tasks(
    writer: Agent, reviewer: Agent
) -> list[Task]:
    """为审核不通过时创建Writer+Reviewer任务对（用inputs传参，无context依赖）."""
    task_writer = Task(
        description=(
            "以下是一份需要修改的短视频脚本。请根据审核意见和博主画像，重新撰写。\n\n"
            "博主画像：\n{strategist_output}\n\n"
            "指定选题：{selected_topic}\n\n"
            "上一版脚本：\n{writer_output}\n\n"
            "请按以下结构输出改进版：\n"
            "1. 开场钩子（前3秒的文案和画面说明，必须抓住注意力）\n"
            "2. 分镜脚本（6-8个分镜）\n"
            "3. 结尾引导\n"
            "4. 3个标题选项\n"
            "5. 拍摄建议"
        ),
        expected_output="一份修改后的完整拍摄脚本",
        agent=writer,
    )

    task_reviewer = Task(
        description=(
            "请审核以下修改后的短视频脚本。\n\n"
            "博主画像：\n{strategist_output}\n\n"
            "指定选题：{selected_topic}\n\n"
            "修改后脚本：\n{writer_output}\n\n"
            "请按以下维度打分（每项1-10分）：\n"
            "1. 钩子强度\n2. 节奏控制\n3. 情绪曲线\n4. 转化设计\n5. 人设匹配度\n\n"
            "综合评分（1-10分）：____\n"
            "审核结论：PASS（7分及以上）/ REVISE（6分及以下）\n"
            "如果REVISE，请列出具体的修改方向和优先级。"
        ),
        expected_output="一份包含5维评分、综合评分和审核结论的审核报告",
        agent=reviewer,
    )

    return [task_writer, task_reviewer]
