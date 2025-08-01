import base64

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from nonebot import get_app, get_bot

from src.common.config import GroupConfig, TaskManager
from src.common.db import SingProgress

app: FastAPI = get_app()


@app.post("/callback/{task_id}")
async def callback(
    task_id: str,
    status: str = Form(...),
    text: str | None = Form(None),
    song_id: str | None = Form(None),
    chunk_index: int | None = Form(None),
    key: int | None = Form(None),
    file: UploadFile | None = File(None),  # noqa: B008
):
    task = await TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    bot_id = task.get("bot_id")
    group_id = task.get("group_id")

    try:
        bot = get_bot(bot_id)
    except Exception:
        return {"message": "failed"}

    # 只要有 song_id、chunk_index、key 就更新
    if group_id and song_id is not None and chunk_index is not None and key is not None:
        config = GroupConfig(group_id)
        sing_progress = SingProgress(
            song_id=str(song_id),
            chunk_index=chunk_index,
            key=key,
        )
        await config.update_sing_progress(sing_progress)

    if status == "failed":
        await TaskManager.remove_task(task_id)
        await bot.call_api(
            "send_group_msg",
            **{
                "message": "我习惯了站着不动思考。有时候啊，也会被大家突然戳一戳，看看睡着了没有。",
                "group_id": group_id,
            },
        )
        return {"message": "ok"}

    elif status == "success":
        if text:
            await bot.call_api(
                "send_group_msg",
                **{
                    "message": text,
                    "group_id": group_id,
                },
            )
        elif file:
            file_content = await file.read()
            base64_file = base64.b64encode(file_content).decode()
            await bot.call_api(
                "send_group_msg",
                **{
                    "message": f"[CQ:record,file=base64://{base64_file}]",
                    "group_id": group_id,
                },
            )

        await TaskManager.remove_task(task_id)
        return {"message": "ok"}
