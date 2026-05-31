import asyncio
import json
import os
import threading
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from src.crew import (
    run_blogger_crew,
    run_strategist_step,
    run_planner_step,
    run_writer_step,
    run_reviewer_step,
    STRATEGIST_DIRECTIONS,
    PLANNER_DIRECTIONS,
)


app = FastAPI(title="抖音博主创作助手")


class RunRequest(BaseModel):
    user_input: str
    selected_topic: str = ""
    template: str = ""


class StepRequest(BaseModel):
    user_input: str
    step: str  # "strategist" | "planner" | "writer" | "reviewer"
    direction: str = ""
    strategist_output: str = ""
    planner_output: str = ""
    writer_output: str = ""
    selected_topic: str = ""
    template: str = ""


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.post("/api/run")
async def run_crew(req: RunRequest):
    """SSE endpoint: run the crew and stream progress events."""
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def progress_callback(event: dict):
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def run_in_thread():
        try:
            outcome = run_blogger_crew(
                user_input=req.user_input,
                selected_topic=req.selected_topic,
                template=req.template,
                progress_callback=progress_callback,
            )
            progress_callback({
                "agent": "✅ 全部完成",
                "stage": "final",
                "output": outcome["result"],
                "step": 99,
                "topics": outcome.get("topics", []),
                "revision_count": outcome.get("revision_count", 0),
            })
        except Exception as exc:
            progress_callback({
                "agent": "❌ 运行出错",
                "stage": "error",
                "output": str(exc),
                "step": -1,
            })

    threading.Thread(target=run_in_thread, daemon=True).start()

    async def event_stream():
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("stage") in ("final", "error"):
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/directions")
async def get_directions():
    return {
        "strategist": STRATEGIST_DIRECTIONS,
        "planner": PLANNER_DIRECTIONS,
    }


@app.post("/api/run-step")
async def run_step(req: StepRequest):
    """SSE endpoint: run a single agent step and stream progress events."""
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def progress_callback(event: dict):
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def run_in_thread():
        try:
            if req.step == "strategist":
                run_strategist_step(
                    user_input=req.user_input,
                    template=req.template,
                    direction=req.direction,
                    progress_callback=progress_callback,
                )
            elif req.step == "planner":
                run_planner_step(
                    user_input=req.user_input,
                    strategist_output=req.strategist_output,
                    direction=req.direction,
                    progress_callback=progress_callback,
                )
            elif req.step == "writer":
                run_writer_step(
                    user_input=req.user_input,
                    strategist_output=req.strategist_output,
                    selected_topic=req.selected_topic,
                    progress_callback=progress_callback,
                )
            elif req.step == "reviewer":
                run_reviewer_step(
                    user_input=req.user_input,
                    strategist_output=req.strategist_output,
                    selected_topic=req.selected_topic,
                    writer_output=req.writer_output,
                    progress_callback=progress_callback,
                )
            else:
                raise ValueError(f"Unknown step: {req.step}")
            progress_callback({
                "agent": "",
                "stage": "complete",
                "output": "",
                "step": -1,
            })
        except Exception as exc:
            progress_callback({
                "agent": "❌ 运行出错",
                "stage": "error",
                "output": str(exc),
                "step": -1,
            })

    threading.Thread(target=run_in_thread, daemon=True).start()

    async def event_stream():
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("stage") in ("complete", "error"):
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7861"))
    uvicorn.run(app, host="0.0.0.0", port=port)
