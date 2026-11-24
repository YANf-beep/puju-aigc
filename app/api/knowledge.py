"""戏曲科普知识库（富媒体版，对应开题报告模块3「戏曲科普知识库」）。

数据源与 RAG 共用同一份知识库（data/knowledge/puju_knowledge.json）——
科普展示与文案生成检索注入同源，保证平台内知识一致性。

富媒体：
- 每条知识可配封面图与视频（AI 生成封面存 data/knowledge_media/{id}.png）；
- video_link：外部视频直达链接（如B站搜索），保证始终有效；
- 上传接口：POST /api/knowledge/{id}/media 上传图片/视频覆盖该条素材。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import config
from ..rag import knowledge as rag

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_cache: Optional[list[dict]] = None

_MEDIA_EXTS = {".png": "image", ".jpg": "image", ".jpeg": "image", ".mp4": "video"}


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        entries = json.loads(config.KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        _cache = [
            {
                "id": e.get("id", i),
                "title": e.get("title", ""),
                "text": e.get("text", ""),
                "video_link": e.get("video_link", ""),
            }
            for i, e in enumerate(entries, 1)
        ]
    return _cache


def _find_media(entry_id: int) -> tuple[Optional[str], Optional[str]]:
    """返回 (cover_url, video_url)：上传/生成的素材优先。"""
    cover = video = None
    for ext in (".png", ".jpg", ".jpeg", ".mp4"):
        p = config.KNOWLEDGE_MEDIA_DIR / f"{entry_id}{ext}"
        if p.is_file():
            if ext == ".mp4":
                video = f"/api/knowledge_media/{p.name}"
            else:
                cover = cover or f"/api/knowledge_media/{p.name}"
    return cover, video


def _entry_dict(e: dict) -> dict:
    cover, video = _find_media(e["id"])
    return {
        "id": e["id"],
        "title": e["title"],
        "text": e["text"],
        "video_link": e.get("video_link", ""),
        "cover": cover,
        "video": video,
    }


def _validate_entry(entry_id: int) -> dict:
    for e in _load():
        if e["id"] == entry_id:
            return e
    raise HTTPException(status_code=404, detail="知识条目不存在")


@router.get("")
def list_knowledge(q: str = "") -> dict:
    items = [_entry_dict(e) for e in _load()]
    if q.strip():
        kw = q.strip()
        hits = [i for i in items if kw in i["title"] or kw in i["text"]]
        if not hits:
            # 关键词未命中时退化为 TF-IDF 相关度检索（种子知识与RAG同源）
            retrieved_titles = {h["title"] for h in rag.retrieve(kw, k=5)}
            hits = [i for i in items if i["title"] in retrieved_titles]
        items = hits
    return {"items": items, "total": len(items)}


# ---------------- 素材上传（科普富媒体） ----------------

@router.post("/{entry_id}/media")
async def upload_media(entry_id: int, file: UploadFile = File(...)) -> dict:
    """为指定知识条目上传封面图或视频（覆盖旧素材；png/jpg/mp4）。"""
    _validate_entry(entry_id)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _MEDIA_EXTS:
        raise HTTPException(
            status_code=400, detail="仅支持 png / jpg / mp4 格式"
        )
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件超过 {config.MAX_UPLOAD_MB}MB 限制")

    # 视频与图片分开存：视频用 .mp4，图片统一存 .png/.jpg（原图格式）
    dest = config.KNOWLEDGE_MEDIA_DIR / f"{entry_id}{ext}"
    dest.write_bytes(data)
    return {
        "entry_id": entry_id,
        "media_type": _MEDIA_EXTS[ext],
        "url": f"/api/knowledge_media/{dest.name}",
    }
