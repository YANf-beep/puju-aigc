"""作品模块：保存生成作品 / 作品广场 / 点赞 / 我的作品（对应开题报告模块3「用户互动」）。

设计要点：
- 保存作品引用任务 task_id，由后端把任务媒体复制到 data/works/（数据库只存路径）；
- 支持图像（png）、视频（mp4）、文案（text）三类作品；
- 作品广场按时间倒序分页，支持按类型筛选；
- 点赞为登录用户切换式（work_likes 关系表）；
- 所有作品带「AI生成」标识（前端徽标），符合AI生成内容标识要求。
"""
from __future__ import annotations

import re
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from . import tasks as tasks_module
from .auth import get_current_user, get_current_user_optional
from .db import User, Work, WorkLike, get_db

router = APIRouter(prefix="/api/works", tags=["works"])
files_router = APIRouter(prefix="/api/files", tags=["files"])

_KIND_LABELS = {
    "image": "戏曲插画",
    "costume": "扮相转换",
    "text": "戏曲文案",
    "video": "短视频",
}


def _work_dict(w: Work, username: str, liked: bool) -> dict:
    media_type = None
    if w.media_file:
        media_type = "video" if w.media_file.endswith(".mp4") else "image"
    return {
        "id": w.id,
        "kind": w.kind,
        "kind_label": _KIND_LABELS.get(w.kind, w.kind),
        "title": w.title,
        "prompt": w.prompt,
        "provider": w.provider,
        "model": w.model,
        "url": f"/api/files/{w.media_file}" if w.media_file else w.remote_url,
        "media_type": media_type,
        "text": w.text_content,
        "like_count": w.like_count,
        "liked": liked,
        "username": username,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "ai_generated": True,  # AI生成内容标识（合规要求）
    }


# ---------------- 保存作品（从生成任务） ----------------

class WorkCreateRequest(BaseModel):
    task_id: str
    title: str = Field(default="", max_length=64)


def _copy_to_works(src_name: str) -> str:
    """把任务媒体复制为作品文件（保留扩展名，新随机名）。"""
    ext = re.search(r"\.(png|mp4|jpg)$", src_name)
    ext = ext.group(0) if ext else ".png"
    dst = f"{uuid.uuid4().hex}{ext}"
    shutil.copyfile(config.TASK_MEDIA_DIR / src_name, config.WORKS_DIR / dst)
    return dst


@router.post("")
def create_work(
    req: WorkCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = tasks_module.get_task_dict(req.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    if task["status"] != "succeeded":
        raise HTTPException(status_code=400, detail=f"任务未成功（当前状态：{task['status']}）")

    kind = task["kind"]  # image / costume / text / video
    title = (req.title or "").strip() or task["kind_label"]
    work = Work(
        user_id=user.id,
        kind=kind,
        title=title,
        prompt=task["prompt"],
        provider=task["provider"],
        model=task["model"],
    )

    if kind in ("image", "costume", "video"):
        items = [i for i in task["items"] if i.get("url", "").startswith("/api/task_media/")]
        if not items:
            # 本地文件缺失时回退外链（罕见：下载失败且留了外链）
            remote = next((i["url"] for i in task["items"] if i["type"] == "image"), None)
            if remote:
                work.remote_url = remote
            else:
                raise HTTPException(status_code=400, detail="任务结果中没有可保存的媒体")
        else:
            src = items[0]["url"].split("/")[-1]
            work.media_file = _copy_to_works(src)
    else:  # text
        if not task["text"]:
            raise HTTPException(status_code=400, detail="任务结果中没有文案内容")
        work.text_content = task["text"]

    db.add(work)
    db.commit()
    return _work_dict(work, user.nickname or str(user.phone), False)


# ---------------- 作品广场 / 我的作品 ----------------

@router.get("")
def list_works(
    kind: str = "",
    page: int = 1,
    page_size: int = 12,
    mine: bool = False,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> dict:
    if mine and user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    q = (
        db.query(Work, User)
        .join(User, Work.user_id == User.id)
        .order_by(Work.created_at.desc(), Work.id.desc())
    )
    if kind in _KIND_LABELS:
        q = q.filter(Work.kind == kind)
    if mine:
        q = q.filter(Work.user_id == user.id)

    total = q.count()
    page = max(1, page)
    page_size = max(1, min(page_size, 48))
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    liked_ids: set = set()
    if user is not None and rows:
        ids = [w.id for w, _ in rows]
        likes = (
            db.query(WorkLike)
            .filter(WorkLike.user_id == user.id, WorkLike.work_id.in_(ids))
            .all()
        )
        liked_ids = {lk.work_id for lk in likes}

    return {
        "items": [
            _work_dict(w, u.nickname or str(u.phone), w.id in liked_ids)
            for w, u in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------------- 点赞（切换） ----------------

@router.post("/{work_id}/like")
def toggle_like(
    work_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    work = db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="作品不存在")
    existing = (
        db.query(WorkLike)
        .filter(WorkLike.user_id == user.id, WorkLike.work_id == work_id)
        .first()
    )
    if existing:
        db.delete(existing)
        work.like_count = max(0, (work.like_count or 0) - 1)
        db.commit()
        return {"liked": False, "like_count": work.like_count}
    db.add(WorkLike(user_id=user.id, work_id=work_id))
    work.like_count = (work.like_count or 0) + 1
    db.commit()
    return {"liked": True, "like_count": work.like_count}


# ---------------- 删除（仅作者） ----------------

@router.delete("/{work_id}")
def delete_work(
    work_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    work = db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="作品不存在")
    if work.user_id != user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的作品")
    db.query(WorkLike).filter(WorkLike.work_id == work_id).delete()
    db.delete(work)
    db.commit()
    return {"deleted": True}


# ---------------- 作品媒体文件服务 ----------------

_WORK_FILE_RE = re.compile(r"^[0-9a-f]{32}\.(png|mp4|jpg)$")


@files_router.get("/{filename}")
def serve_file(filename: str):
    """只允许访问 data/works 下的合法命名文件（防路径穿越）。"""
    if not _WORK_FILE_RE.match(filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    path = config.WORKS_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    media_type = "video/mp4" if filename.endswith(".mp4") else "image/png"
    return FileResponse(path, media_type=media_type)
