"""离线冒烟测试（无需任何 API Key）：python tests/smoke_test.py

覆盖：双层提示词组装（含视频）/ RAG检索 / Provider工厂 / mock生成（图像·文案·视频）/
持久化任务流（create_task → 执行 → get_task_dict）。
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# 必须在导入 app 包之前设置（app.config 在导入时读取环境变量）
os.environ.setdefault("IMAGE_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("VIDEO_PROVIDER", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import ConfigError  # noqa: E402
from app.api.db import init_db  # noqa: E402
from app.prompts import opera_templates as T  # noqa: E402
from app.providers import get_image_provider, get_llm_provider, get_video_provider  # noqa: E402
from app.rag import knowledge as rag  # noqa: E402

init_db()  # 任务表等建表（生产环境由 FastAPI lifespan 触发）

PASS, FAIL = "✓ PASS", "✗ FAIL"
_results: list[tuple[str, bool, str]] = []


def check(name: str, fn) -> None:
    try:
        detail = fn() or ""
        _results.append((name, True, detail))
        print(f"{PASS}  {name} {detail}")
    except Exception as e:  # noqa: BLE001
        _results.append((name, False, str(e)))
        print(f"{FAIL}  {name} -> {type(e).__name__}: {e}")


def t_prompt_build() -> str:
    p = T.build_image_prompt("净", "靠甲", "古戏台", "威武", "手持马鞭")
    assert "脸谱" in p and "靠旗" in p and "古戏台" in p and "手持马鞭" in p
    return f"长度{len(p)}字"


def t_costume_prompt() -> str:
    p = T.build_costume_prompt("旦", "红色女帔")
    assert "旦行" in p and "保留人物面部特征" in p and "红色女帔" in p
    return "ok"


def t_video_prompt() -> str:
    p = T.build_video_prompt("净", "靠甲", "舞台", "甩袖转身，靠旗猎猎作响")
    assert "脸谱" in p and "靠旗" in p and "甩袖转身" in p and "视频" in p
    return f"长度{len(p)}字"


def t_copy_messages() -> str:
    sys_msg, user_msg = T.build_copy_messages("蒲剧唱腔", "科普短文", ["唱腔特点：慷慨激越"])
    assert "蒲剧" in sys_msg and "【领域知识1】" in user_msg
    return "ok"


def t_rag_retrieve() -> str:
    hits = rag.retrieve("蒲剧的唱腔有什么特点", k=3)
    assert hits and hits[0]["title"] == "唱腔特点", f"top1={hits[0]['title'] if hits else None}"
    return f"top1相关度{hits[0]['score']}"


def t_mock_providers() -> str:
    img = get_image_provider("mock")
    imgs = img.text_to_image("测试", size="512x512", n=2)
    assert len(imgs) == 2 and imgs[0].data[:8] == b"\x89PNG\r\n\x1a\n"
    llm = get_llm_provider("mock")
    text = llm.chat("s", "u")
    assert "蒲剧" in text
    vid = get_video_provider("mock")
    rid = vid.create_video("蒲剧亮相", duration=5, resolution="720p")
    st = vid.poll_video(rid)
    assert st.status == "succeeded" and st.local_file
    from pathlib import Path as P
    assert P(st.local_file).is_file()
    return "图像×2 + 文案 + 视频(mock) OK"


def t_factory_unknown() -> str:
    try:
        get_image_provider("不存在的平台")
    except ConfigError:
        return "正确抛出ConfigError"
    raise AssertionError("未抛出ConfigError")


def t_task_flow_image() -> str:
    from app.api import tasks as tm

    tid = tm.create_task("image", prompt="测试提示词", provider="mock", params={"size": "512x512"})
    asyncio.run(tm._run_image_task(tid, "mock", "测试提示词", "512x512", 1))
    d = tm.get_task_dict(tid)
    assert d["status"] == "succeeded", f"{d['status']}: {d.get('error')}"
    assert d["items"] and d["items"][0]["url"].startswith("/api/task_media/")
    return f"task={tid}"


def t_task_flow_text() -> str:
    from app.api import tasks as tm

    tid = tm.create_task("text", prompt="u", provider="mock")
    asyncio.run(tm._run_text_task(tid, "mock", "sys", "user"))
    d = tm.get_task_dict(tid)
    assert d["status"] == "succeeded" and "蒲剧" in (d["text"] or "")
    return f"task={tid}"


def t_task_flow_video() -> str:
    from app.api import tasks as tm

    tid = tm.create_task("video", prompt="蒲剧亮相", provider="mock", params={"duration": 5})
    asyncio.run(tm._run_video_task(tid, "mock", "蒲剧亮相", 5, "720p", "adaptive", None))
    d = tm.get_task_dict(tid)
    assert d["status"] == "succeeded", f"{d['status']}: {d.get('error')}"
    assert d["items"] and d["items"][0]["type"] == "video"
    return f"task={tid} -> {d['items'][0]['url']}"


def t_task_list() -> str:
    from app.api import tasks as tm

    items = tm.list_tasks(ids=None, limit=10)
    assert isinstance(items, list)
    return f"共{len(items)}条"


if __name__ == "__main__":
    print("=" * 56)
    print("puju-aigc 离线冒烟测试（mock模式，无需API Key）")
    print("=" * 56)
    check("双层提示词·插画", t_prompt_build)
    check("扮相转换指令", t_costume_prompt)
    check("双层提示词·视频", t_video_prompt)
    check("文案提示词+知识注入", t_copy_messages)
    check("RAG知识检索", t_rag_retrieve)
    check("Mock三类生成（图/文/视频）", t_mock_providers)
    check("工厂未知服务报错", t_factory_unknown)
    check("持久化任务·图像", t_task_flow_image)
    check("持久化任务·文案", t_task_flow_text)
    check("持久化任务·视频", t_task_flow_video)
    check("任务列表", t_task_list)
    failed = [r for r in _results if not r[1]]
    print("-" * 56)
    if failed:
        print(f"结果：{len(_results) - len(failed)}/{len(_results)} 通过，存在失败项！")
        sys.exit(1)
    print(f"结果：{len(_results)}/{len(_results)} 全部通过 ✅")
