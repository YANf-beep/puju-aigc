"""全链路集成测试（mock模式，无需任何API Key）：python tests/test_api_full.py

覆盖：手机号注册/登录/JWT → 知识库（视频链接/富媒体字段）→ 生成任务(HTTP提交+轮询：
图像/文案/视频) → 任务列表 → 保存作品（图像/视频/文案）→ 作品广场 → 点赞 →
文件服务（含mp4）→ 删除 → 科普素材上传 → 静态站点托管。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 必须在导入 app 之前设置（app.config 在导入时读取环境变量）
os.environ.setdefault("IMAGE_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("VIDEO_PROVIDER", "mock")
_TEST_DB = ROOT / "data" / "test_api.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["WORKS_DIR"] = str(ROOT / "data" / "test_works")

sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.api.main import app  # noqa: E402

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


def wait_task(client: TestClient, task_id: str, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = client.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("succeeded", "failed"):
            return task
        time.sleep(0.5)
    raise AssertionError(f"任务超时：{task_id}")


def t_full_flow() -> str:
    with TestClient(app) as client:
        # 1. 手机号注册/登录/me
        phone = f"138{int(time.time()) % 10**8:08d}"
        r = client.post("/api/auth/register", json={"phone": phone, "password": "abc12345"})
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        nickname = r.json()["user"]["nickname"]
        assert nickname.startswith("戏迷"), nickname
        headers = {"Authorization": f"Bearer {token}"}
        me = client.get("/api/auth/me", headers=headers).json()
        assert me["phone"] == phone

        # 错误手机号 422 / 重复注册 400 / 错误密码 401
        assert client.post("/api/auth/register", json={"phone": "12345", "password": "abc12345"}).status_code == 422
        assert client.post("/api/auth/register", json={"phone": phone, "password": "abc12345"}).status_code == 400
        assert client.post("/api/auth/login", json={"phone": phone, "password": "wrong!"}).status_code == 401

        # 2. 知识库（含视频链接）
        kn = client.get("/api/knowledge").json()
        assert kn["total"] >= 10
        assert all("video_link" in e and "cover" in e for e in kn["items"])

        # 3. 图像任务：提交 → 轮询 → 保存
        r = client.post("/api/generate/image", json={"role": "净", "free_text": "手持马鞭", "n": 1})
        assert r.status_code == 200, r.text
        img_task = wait_task(client, r.json()["task_id"])
        assert img_task["status"] == "succeeded", img_task.get("error")
        assert img_task["items"][0]["url"].startswith("/api/task_media/")

        r = client.post("/api/works", json={"task_id": img_task["task_id"], "title": "净角测试"}, headers=headers)
        assert r.status_code == 200, r.text
        work = r.json()
        assert work["ai_generated"] and work["url"].startswith("/api/files/")
        wid = work["id"]
        assert client.post("/api/works", json={"task_id": img_task["task_id"]}).status_code == 401

        # 4. 视频任务：提交 → 轮询 → 保存 → mp4服务
        r = client.post("/api/generate/video", json={"role": "旦", "free_text": "水袖轻扬", "duration": 5})
        assert r.status_code == 200, r.text
        vid_task = wait_task(client, r.json()["task_id"], timeout=90)
        assert vid_task["status"] == "succeeded", vid_task.get("error")
        assert vid_task["kind"] == "video" and vid_task["items"][0]["type"] == "video"

        r = client.post("/api/works", json={"task_id": vid_task["task_id"], "title": "水袖视频"}, headers=headers)
        assert r.status_code == 200, r.text
        vwork = r.json()
        assert vwork["kind"] == "video" and vwork["media_type"] == "video"
        fresp = client.get(vwork["url"])
        assert fresp.status_code == 200 and "video" in fresp.headers.get("content-type", "")

        # 5. 任务列表（本地ids + 登录用户）
        r = client.post("/api/tasks/list", json={"ids": [img_task["task_id"], vid_task["task_id"]]}, headers=headers)
        ids = [t["task_id"] for t in r.json()["items"]]
        assert img_task["task_id"] in ids and vid_task["task_id"] in ids

        # 6. 文案任务与作品
        r = client.post("/api/generate/text", json={"subject": "蒲剧唱腔特点", "use_rag": True})
        assert len(r.json()["knowledge_used"]) >= 1
        txt_task = wait_task(client, r.json()["task_id"])
        assert txt_task["status"] == "succeeded" and "蒲剧" in txt_task["text"]
        r = client.post("/api/works", json={"task_id": txt_task["task_id"]}, headers=headers)
        assert r.status_code == 200 and r.json()["kind"] == "text"

        # 7. 广场 / 点赞 / 我的作品 / 删除
        gallery = client.get("/api/works").json()
        assert gallery["total"] >= 3
        video_filter = client.get("/api/works", params={"kind": "video"}).json()
        assert any(w["id"] == vwork["id"] for w in video_filter["items"])
        lk = client.post(f"/api/works/{wid}/like", headers=headers).json()
        assert lk == {"liked": True, "like_count": 1}
        assert client.post(f"/api/works/{wid}/like", headers=headers).json()["liked"] is False
        mine = client.get("/api/works", params={"mine": "true"}, headers=headers).json()
        assert mine["total"] >= 3
        assert client.delete(f"/api/works/{wid}", headers=headers).json()["deleted"] is True

        # 8. 科普素材上传（图片）
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), (200, 60, 50)).save(buf, format="PNG")
        r = client.post(
            "/api/knowledge/1/media",
            files={"file": ("cover.png", buf.getvalue(), "image/png")},
        )
        assert r.status_code == 200, r.text
        kn2 = client.get("/api/knowledge", params={"q": "剧种概况"}).json()
        assert kn2["items"][0]["cover"] and kn2["items"][0]["cover"].startswith("/api/knowledge_media/")
        cover_resp = client.get(kn2["items"][0]["cover"])
        assert cover_resp.status_code == 200 and cover_resp.content[:4] == b"\x89PNG"

        # 9. 路径穿越防护
        for trav in ["/api/files/../../app/config.py", "/api/task_media/xx.png", "/api/knowledge_media/abc.php"]:
            tr = client.get(trav)
            assert tr.status_code in (200, 400, 404)
            low = tr.content.lower()
            assert b"secret_key" not in low and b"database_url" not in low

        return f"用户{phone}，图像/视频/文案任务与作品全通，视频作品#{vwork['id']}"
    return ""


def t_static_site() -> str:
    dist = ROOT / "puju-web" / "dist" / "index.html"
    if not dist.is_file():
        return "（跳过：前端未构建）"
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200 and 'id="app"' in r.text
        r2 = client.get("/create")
        assert r2.status_code == 200 and 'id="app"' in r2.text
        assert client.get("/api/notexist").status_code == 404
    return "index.html + SPA回退 + /api隔离 OK"


if __name__ == "__main__":
    print("=" * 56)
    print("puju-aigc 全链路集成测试（mock模式）")
    print("=" * 56)
    check("全流程：手机号/知识库/三类任务/作品/点赞/上传/穿越防护", t_full_flow)
    check("静态站点托管（若已构建前端）", t_static_site)
    failed = [r for r in _results if not r[1]]
    print("-" * 56)
    if failed:
        print(f"结果：{len(_results) - len(failed)}/{len(_results)} 通过，存在失败项！")
        sys.exit(1)
    print(f"结果：{len(_results)}/{len(_results)} 全部通过 ✅")
