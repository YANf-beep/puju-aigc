"""FastAPI 应用入口（对应开题报告模块3）。

组装内容：
- 生成服务：/api/generate/*（图像/扮相/文案/视频）+ /api/tasks*（持久化任务）
- 用户系统：/api/auth/*（手机号注册/登录，JWT）
- 用户互动：/api/works*（作品广场/点赞/我的作品）+ /api/files/*（作品媒体）
- 科普知识库：/api/knowledge（富媒体条目）+ /api/knowledge/{id}/media（素材上传）
- 前端托管：puju-web/dist 存在时直接托管为完整网站

启动（完整网站，一条命令）：
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
    → 浏览器打开 http://localhost:8000
接口文档：http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import config
from ..prompts import opera_templates as T
from ..rag import knowledge as rag
from ..providers import (
    image_provider_options,
    llm_provider_options,
    video_provider_options,
)
from . import auth as auth_module
from . import knowledge as knowledge_module
from . import tasks as tasks_module
from . import works as works_module
from .auth import get_current_user_optional
from .db import User, init_db
from .tasks import create_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # 恢复上次未完成的任务（视频续查、其余标记失败）——任务不丢失的关键
    await tasks_module.recover_interrupted_tasks()
    yield


app = FastAPI(
    title="蒲剧数字活化平台",
    version="0.3.0",
    description="多模型服务适配层 + 双层提示词 + 轻量RAG + 持久化任务队列 + 用户互动",
    lifespan=lifespan,
)

# 供 Vue3 本地开发跨域调试（npm run dev: 5173）；整站部署时前后端同源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_module.router)
app.include_router(works_module.router)
app.include_router(works_module.files_router)
app.include_router(knowledge_module.router)


# ---------------- 请求模型 ----------------

class ImageGenRequest(BaseModel):
    role: str = "净"
    costume: str = "蟒袍"
    scene: str = "舞台"
    mood: str = "威武"
    free_text: str = ""
    size: str = "2K"
    n: int = Field(default=1, ge=1, le=4)
    provider: Optional[str] = None


class TextGenRequest(BaseModel):
    subject: str
    style: str = "科普短文"
    use_rag: bool = True
    provider: Optional[str] = None


class VideoGenRequest(BaseModel):
    """短视频生成（Seedance）：双层提示词 + 动态描述 + 可选首帧图。"""

    role: str = "净"
    costume: str = "蟒袍"
    scene: str = "舞台"
    free_text: str = ""
    duration: int = Field(default=10, description="5或10秒")
    resolution: str = "720p"
    ratio: str = "adaptive"
    first_frame_b64: Optional[str] = None  # 图生视频：首帧图（base64，不含data:前缀）
    provider: Optional[str] = None


class TaskListRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=100)


# ---------------- 基础接口 ----------------

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "image_provider": config.IMAGE_PROVIDER,
        "llm_provider": config.LLM_PROVIDER,
        "video_provider": config.VIDEO_PROVIDER,
    }


@app.get("/api/providers")
def providers() -> dict:
    return {
        "image": image_provider_options(),
        "llm": llm_provider_options(),
        "video": video_provider_options(),
        "defaults": {
            "image": config.IMAGE_PROVIDER,
            "llm": config.LLM_PROVIDER,
            "video": config.VIDEO_PROVIDER,
        },
    }


@app.get("/api/templates")
def templates() -> dict:
    """双层提示词第一层的取值（由后端统一下发，与提示词模板库同源）。"""
    return {
        "roles": list(T.ROLE_PRESETS.keys()),
        "costumes": list(T.COSTUME_PRESETS.keys()),
        "scenes": list(T.SCENE_PRESETS.keys()),
        "moods": list(T.MOOD_PRESETS.keys()),
        "copy_styles": list(T.COPY_STYLES),
        "sizes": ["2K", "4K"],
        "video_durations": [5, 10],
        "video_resolutions": ["720p", "1080p"],
    }


# ---------------- 生成接口（提交即返回，结果走任务中心） ----------------

@app.post("/api/generate/image")
async def generate_image(
    req: ImageGenRequest, user: Optional[User] = Depends(get_current_user_optional)
) -> dict:
    prompt = T.build_image_prompt(
        role=req.role, costume=req.costume, scene=req.scene,
        mood=req.mood, free_text=req.free_text,
    )
    tid = create_task(
        "image", user_id=user.id if user else None, prompt=prompt,
        provider=req.provider or config.IMAGE_PROVIDER,
        params={"size": req.size, "n": req.n},
    )
    asyncio.create_task(
        tasks_module._run_image_task(tid, req.provider, prompt, req.size, req.n)
    )
    return {"task_id": tid, "status": "pending", "prompt": prompt}


@app.post("/api/generate/costume")
async def generate_costume(
    image: UploadFile = File(..., description="用户照片"),
    role: str = Form("净"),
    free_text: str = Form(""),
    provider: Optional[str] = Form(None),
    user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    prompt = T.build_costume_prompt(role, free_text)
    image_bytes = await image.read()
    tid = create_task(
        "costume", user_id=user.id if user else None, prompt=prompt,
        provider=provider or config.IMAGE_PROVIDER,
    )
    asyncio.create_task(tasks_module._run_costume_task(tid, provider, image_bytes, prompt))
    return {"task_id": tid, "status": "pending", "prompt": prompt}


@app.post("/api/generate/text")
async def generate_text(
    req: TextGenRequest, user: Optional[User] = Depends(get_current_user_optional)
) -> dict:
    knowledge_hits = rag.retrieve(req.subject, k=3) if req.use_rag else []
    snippets = rag.format_snippets(knowledge_hits)
    system, user_prompt = T.build_copy_messages(req.subject, req.style, snippets)
    tid = create_task(
        "text", user_id=user.id if user else None, prompt=user_prompt,
        provider=req.provider or config.LLM_PROVIDER,
    )
    asyncio.create_task(tasks_module._run_text_task(tid, req.provider, system, user_prompt))
    return {"task_id": tid, "status": "pending", "knowledge_used": snippets}


@app.post("/api/generate/video")
async def generate_video(
    req: VideoGenRequest, user: Optional[User] = Depends(get_current_user_optional)
) -> dict:
    if req.duration not in (5, 10):
        raise HTTPException(status_code=400, detail="duration 仅支持 5 或 10 秒")
    prompt = T.build_video_prompt(
        role=req.role, costume=req.costume, scene=req.scene, free_text=req.free_text
    )
    first_frame = None
    if req.first_frame_b64:
        import base64
        try:
            first_frame = base64.b64decode(req.first_frame_b64)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="首帧图 base64 解析失败") from exc
    tid = create_task(
        "video", user_id=user.id if user else None, prompt=prompt,
        provider=req.provider or config.VIDEO_PROVIDER,
        params={
            "duration": req.duration, "resolution": req.resolution,
            "ratio": req.ratio, "with_first_frame": bool(first_frame),
        },
    )
    asyncio.create_task(
        tasks_module._run_video_task(
            tid, req.provider, prompt, req.duration, req.resolution, req.ratio, first_frame
        )
    )
    return {
        "task_id": tid, "status": "pending", "prompt": prompt,
        "note": "视频生成通常需要2~5分钟，可关闭页面，稍后在任务中心查看",
    }


# ---------------- 任务查询（持久化：刷新/重启不丢） ----------------

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = tasks_module.get_task_dict(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.post("/api/tasks/list")
def list_tasks(
    req: TaskListRequest, user: Optional[User] = Depends(get_current_user_optional)
) -> dict:
    """任务中心：登录用户的任务 ∪ 本浏览器提交的任务（localStorage ids）。"""
    items = tasks_module.list_tasks(
        user_id=user.id if user else None, ids=req.ids or None
    )
    return {"items": items, "total": len(items)}


# ---------------- 任务媒体文件服务 ----------------

_TASK_MEDIA_RE = re.compile(r"^[0-9a-f]{12}_\d+\.(png|mp4|jpg)$")


@app.get("/api/task_media/{filename}")
def serve_task_media(filename: str):
    if not _TASK_MEDIA_RE.match(filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    path = config.TASK_MEDIA_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    media_type = "video/mp4" if filename.endswith(".mp4") else "image/png"
    return FileResponse(path, media_type=media_type)


# ---------------- 科普媒体文件服务 ----------------

_KNOWLEDGE_MEDIA_RE = re.compile(r"^\d+\.(png|jpg|jpeg|mp4)$")


@app.get("/api/knowledge_media/{filename}")
def serve_knowledge_media(filename: str):
    if not _KNOWLEDGE_MEDIA_RE.match(filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    path = config.KNOWLEDGE_MEDIA_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    if filename.endswith(".mp4"):
        media_type = "video/mp4"
    elif filename.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    else:
        media_type = "image/png"
    return FileResponse(path, media_type=media_type)


# ---------------- 前端托管（Vue3 dist 存在时 → 完整网站） ----------------

_dist = config.WEB_DIST_DIR
if (_dist / "index.html").is_file():
    if (_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        """SPA回退：非 /api 路径统一回退到 index.html（前端路由由 vue-router 接管）。"""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        target = _dist / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(_dist / "index.html")
