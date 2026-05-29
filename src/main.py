import gradio as gr
from src.crew import run_blogger_crew


def run_pipeline(blogger_info: str, selected_topic: str) -> str:
    """供Gradio调用的包装函数."""
    if not blogger_info.strip():
        return "## 请输入博主定位信息"
    try:
        result = run_blogger_crew(
            user_input=blogger_info.strip(),
            selected_topic=selected_topic.strip() if selected_topic else "",
        )
        return f"## 生成结果\n\n{result}"
    except Exception as e:
        return f"## 运行出错\n\n```\n{str(e)}\n```"


def build_ui():
    with gr.Blocks(title="博主创作助手", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🎬 博主创作多Agent助手")
        gr.Markdown("输入你的博主定位，AI团队帮你完成选题策划和脚本创作。")

        with gr.Row():
            with gr.Column(scale=1):
                blogger_info = gr.Textbox(
                    label="博主定位",
                    placeholder=(
                        "例：我是做美妆教程的博主，粉丝以18-25岁女性为主，"
                        "风格偏实用干货，希望内容有干货也有情绪共鸣..."
                    ),
                    lines=5,
                )
                topic_hint = gr.Textbox(
                    label="主题方向（可选）",
                    placeholder="留空则由选题策划师自动推荐最佳方向",
                    lines=2,
                )
                run_btn = gr.Button("开始创作", variant="primary")

            with gr.Column(scale=2):
                output = gr.Markdown(
                    value="### 等待输入...\n\n输入博主信息后点击「开始创作」，AI团队将依次完成：\n"
                          "1. 🎯 博主画像分析\n2. 🔥 选题策划\n3. ✍️ 脚本撰写\n4. 🔍 质量审核",
                )

        run_btn.click(
            fn=run_pipeline,
            inputs=[blogger_info, topic_hint],
            outputs=output,
        )

    return app


if __name__ == "__main__":
    app = build_ui()
    app.launch(server_name="127.0.0.1", server_port=7860)
