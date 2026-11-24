"""创作任务机制（持久化版）——对应开题报告模块3「异步任务机制」的升级。

设计目标：用户提交创作后，刷新页面 / 关闭网页 / 重启服务，任务与结果均不丢失，
且支持多任务并行。实现要点：

- 任务记录落库（tasks 表），任务中心跨会话可见；
- 图像/文案/扮相：本地异步执行（线程池），完成时媒体立即落盘 data/task_media/
  （平台返回的外链有时效，落盘才能长期保存）；
- 视频：走平台异步任务（Seedance：提交 → 轮询），remote_task_id 落库，
  服务重启后自动续查；
- 重启恢复：视频任务续查；其余中断任务标记失败并提示重新生成。
"""
from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests as http_requests
from sqlalchemy import or_

from .. import config
from ..providers import get_image_provider, get_llm_provider, get_video_provider
from .db import SessionLocal, Task

KIND_LABELS = {
    "image": "戏曲插画",
    "costume": "扮相转换",
    "text": "戏曲文案",
    "video": "短视频",
}
ACTIVE_STATUSES = ("pending", "running")

VIDEO_POLL_INTERVAL = 8       # 视频轮询间隔（秒）
VIDEO_WATCH_TIMEOUT = 1800    # 视频任务最长等待（30分钟）


# ---------------- 基础操作 ----------------

def create_task(
    kind: str,
    *,
    user_id: Optional[int] = None,
    prompt: str = "",
    provider: str = "",
    model: str = "",
    params: Optional[dict] = None,
) -> str:
    tid = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        db.add(
            Task(
                id=tid,
                user_id=user_id,
                kind=kind,
                status="pending",
                prompt=prompt,
                provider=provider,
                model=model,
                params=json.dumps(params or {}, ensure_ascii=False),
            )
        )
        db.commit()
    return tid


def _update(tid: str, **fields) -> None:
    with SessionLocal() as db:
        task = db.get(Task, tid)
        if task is None:
            return
        for k, v in fields.items():
            setattr(task, k, v)
        task.updated_at = datetime.utcnow()
        db.commit()


def get_task_dict(tid: str) -> Optional[dict]:
    with SessionLocal() as db:
        task = db.get(Task, tid)
        return task_to_dict(task) if task else None


def task_to_dict(t: Task) -> dict:
    """任务 → API字典（items 为可直接展示的媒体列表）。"""
    try:
        params = json.loads(t.params or "{}")
    except Exception:  # noqa: BLE001
        params = {}
    try:
        result = json.loads(t.result) if t.result else None
    except Exception:  # noqa: BLE001
        result = None

    items: list[dict] = []
    if result:
        for f in result.get("files", []):
            ext = Path(f).suffix.lower()
            items.append(
                {
                    "type": "video" if ext == ".mp4" else "image",
                    "url": f"/api/task_media/{f}",
                }
            )
        for u in result.get("urls", []):  # 外链兜底（本地落盘失败时）
            items.append({"type": "image", "url": u})

    return {
        "task_id": t.id,
        "kind": t.kind,
        "kind_label": KIND_LABELS.get(t.kind, t.kind),
        "status": t.status,
        "prompt": t.prompt,
        "provider": t.provider,
        "model": t.model,
        "params": params,
        "items": items,
        "text": (result or {}).get("text"),
        "error": t.error,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def list_tasks(
    user_id: Optional[int] = None, ids: Optional[list[str]] = None, limit: int = 50
) -> list[dict]:
    """任务中心数据：登录用户的任务 ∪ 本浏览器提交的任务（localStorage ids）。"""
    with SessionLocal() as db:
        q = db.query(Task)
        conds = []
        if user_id is not None:
            conds.append(Task.user_id == user_id)
        if ids:
            conds.append(Task.id.in_(ids))
        if conds:
            q = q.filter(or_(*conds))
        tasks = q.order_by(Task.created_at.desc(), Task.id.desc()).limit(limit).all()
        return [task_to_dict(t) for t in tasks]


# ---------------- 媒体落盘 ----------------

def _save_task_media(tid: str, data: bytes, index: int, ext: str) -> str:
    name = f"{tid}_{index}{ext}"
    (config.TASK_MEDIA_DIR / name).write_bytes(data)
    return name


async def _download_to_file(url: str, dest: Path, timeout: int = 300) -> None:
    def _get():
        r = http_requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content

    dest.write_bytes(await asyncio.to_thread(_get))


# ---------------- 任务执行体 ----------------

async def _run_image_task(
    tid: str, provider: Optional[str], prompt: str, size: str, n: int
) -> None:
    """戏曲插画生成（kind=image）。"""
    _update(tid, status="running")
    try:
        prov = get_image_provider(provider)
        images = await asyncio.to_thread(prov.text_to_image, prompt, size=size, n=n)
        files: list[str] = []
        urls: list[str] = []
        for i, g in enumerate(images):
            if g.data:
                files.append(_save_task_media(tid, g.data, i, ".png"))
            elif g.url:
                try:  # 外链落盘（平台URL有时效），失败则保留外链
                    dest = config.TASK_MEDIA_DIR / f"{tid}_{i}.png"
                    await _download_to_file(g.url, dest)
                    files.append(dest.name)
                except Exception:  # noqa: BLE001
                    urls.append(g.url)
        if not files and not urls:
            raise RuntimeError("生成结果为空")
        _update(
            tid,
            status="succeeded",
            model=images[0].model if images else "",
            result=json.dumps({"files": files, "urls": urls}, ensure_ascii=False),
        )
    except Exception as exc:  # noqa: BLE001 —— 失败原因需回传客户端
        _update(tid, status="failed", error=f"{type(exc).__name__}: {exc}")


async def _run_costume_task(
    tid: str, provider: Optional[str], image: bytes, prompt: str
) -> None:
    """照片扮相转换（kind=costume）。"""
    _update(tid, status="running")
    try:
        prov = get_image_provider(provider)
        if not prov.supports_edit:
            raise NotImplementedError(
                f"图像服务 [{prov.name}] 不支持图像编辑，扮相转换请使用 ark（Seedream参考图编辑）。"
            )
        images = await asyncio.to_thread(prov.edit_image, image, prompt)
        files: list[str] = []
        urls: list[str] = []
        for i, g in enumerate(images):
            if g.data:
                files.append(_save_task_media(tid, g.data, i, ".png"))
            elif g.url:
                try:
                    dest = config.TASK_MEDIA_DIR / f"{tid}_{i}.png"
                    await _download_to_file(g.url, dest)
                    files.append(dest.name)
                except Exception:  # noqa: BLE001
                    urls.append(g.url)
        if not files and not urls:
            raise RuntimeError("生成结果为空")
        _update(
            tid,
            status="succeeded",
            model=images[0].model if images else "",
            result=json.dumps({"files": files, "urls": urls}, ensure_ascii=False),
        )
    except Exception as exc:  # noqa: BLE001
        _update(tid, status="failed", error=f"{type(exc).__name__}: {exc}")


async def _run_text_task(
    tid: str, provider: Optional[str], system: str, user: str
) -> None:
    """戏曲文案生成（kind=text）。"""
    _update(tid, status="running")
    try:
        prov = get_llm_provider(provider)
        text = await asyncio.to_thread(prov.chat, system, user)
        _update(tid, status="succeeded", result=json.dumps({"text": text}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        _update(tid, status="failed", error=f"{type(exc).__name__}: {exc}")


# ---------------- 视频（异步任务式） ----------------

async def _run_video_task(
    tid: str,
    provider: Optional[str],
    prompt: str,
    duration: int,
    resolution: str,
    ratio: str,
    first_frame: Optional[bytes],
) -> None:
    """短视频生成（kind=video）：提交平台任务并轮询至完成。"""
    _update(tid, status="running")
    try:
        prov = get_video_provider(provider)

        def _submit():
            return prov.create_video(
                prompt,
                duration=duration,
                resolution=resolution,
                ratio=ratio,
                first_frame=first_frame,
            )

        remote_id = await asyncio.to_thread(_submit)
        _update(tid, remote_task_id=remote_id, model=getattr(prov, "video_model", ""))
        await _watch_video(tid, provider, remote_id)
    except Exception as exc:  # noqa: BLE001
        _update(tid, status="failed", error=f"{type(exc).__name__}: {exc}")


async def _watch_video(tid: str, provider: Optional[str], remote_id: str) -> None:
    """轮询视频任务直至完成/失败/超时。服务重启后可凭 remote_task_id 再次调用续查。"""
    prov = get_video_provider(provider)
    deadline = time.monotonic() + VIDEO_WATCH_TIMEOUT
    while time.monotonic() < deadline:
        st = await asyncio.to_thread(prov.poll_video, remote_id)
        if st.status == "succeeded":
            files: list[str] = []
            if st.local_file:  # mock等本地模式
                src = Path(st.local_file)
                ext = src.suffix.lower() or ".mp4"
                name = f"{tid}_0{ext}"
                shutil.copyfile(src, config.TASK_MEDIA_DIR / name)
                files.append(name)
            elif st.video_url:
                dest = config.TASK_MEDIA_DIR / f"{tid}_0.mp4"
                await _download_to_file(st.video_url, dest)
                files.append(dest.name)
            if not files:
                _update(tid, status="failed", error="视频生成完成但未取得文件")
                return
            _update(tid, status="succeeded", result=json.dumps({"files": files}))
            return
        if st.status == "failed":
            _update(tid, status="failed", error=st.error or "视频生成失败")
            return
        await asyncio.sleep(VIDEO_POLL_INTERVAL)
    _update(tid, status="failed", error="视频生成超时（超过30分钟），请重试")


# ---------------- 重启恢复 ----------------

async def recover_interrupted_tasks() -> None:
    """服务启动时恢复未完成任务：视频续查，其余标记失败（FastAPI lifespan 调用）。"""
    with SessionLocal() as db:
        interrupted = db.query(Task).filter(Task.status.in_(ACTIVE_STATUSES)).all()
        items = [(t.id, t.kind, t.provider, t.remote_task_id) for t in interrupted]
    for tid, kind, provider_name, remote_id in items:
        if kind == "video" and remote_id:
            asyncio.create_task(_watch_video(tid, provider_name or "ark", remote_id))
        else:
            _update(tid, status="failed", error="服务重启导致任务中断，请重新生成")
