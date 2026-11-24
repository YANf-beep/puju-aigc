"""Mock Provider：离线开发与冒烟测试，零Key零成本。

用途：
1. 未配置任何密钥时跑通「提示词组装 → 生成 → 展示」全流程；
2. tests/ 验证 FastAPI 异步任务链路（含视频任务的提交/轮询/落盘）；
3. 演示「双层提示词机制」的提示词组装效果。
"""
from __future__ import annotations

import random
import shutil
import subprocess
import tempfile
import time
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from .base import GeneratedImage, ImageProvider, LLMProvider, VideoProvider, VideoTaskStatus


def _parse_size(size: str) -> tuple[int, int]:
    try:
        w, h = size.lower().split("x")
        return max(256, min(int(w), 2048)), max(256, min(int(h), 2048))
    except Exception:
        return 1024, 1024


def _placeholder(text: str, size: str) -> bytes:
    """生成一张带标注的占位图（纯ASCII文字，避免中文字体缺失问题）。"""
    w, h = _parse_size(size)
    img = Image.new("RGB", (w, h), color=(178, 58, 46))  # 戏曲红
    draw = ImageDraw.Draw(img)
    for y in range(0, h, 8):  # 简单纹理
        draw.line([(0, y), (w, y)], fill=(160, 48, 38), width=1)
    draw.text((24, 24), "MOCK IMAGE - Puju AIGC Platform", fill="white")
    draw.text((24, 56), f"size={w}x{h}", fill="white")
    draw.text((24, 88), text[:80], fill="white")
    draw.text((24, h - 40), "(offline mock, no API call)", fill=(255, 220, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class MockImageProvider(ImageProvider):
    name = "mock（离线·开发测试）"

    def text_to_image(
        self, prompt: str, *, size: str = "1024x1024", n: int = 1
    ) -> list[GeneratedImage]:
        tag = f"t2i | prompt[{len(prompt)}chars]: {prompt[:60]}"
        return [
            GeneratedImage(
                provider="mock",
                model="mock-image",
                data=_placeholder(tag + f" #{i + 1}", size),
            )
            for i in range(max(1, n))
        ]

    def edit_image(
        self, image: bytes, prompt: str, **kwargs
    ) -> list[GeneratedImage]:
        tag = f"i2i(costume) | {prompt[:60]}"
        return [
            GeneratedImage(provider="mock", model="mock-edit", data=_placeholder(tag, "1024x1024"))
        ]


class MockLLMProvider(LLMProvider):
    name = "mock（离线·开发测试）"

    def chat(
        self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        _ = random.random()  # 演示可复现的非随机路径
        return (
            "【离线Mock文案】当前未连接大模型API，以下为流程演示输出。\n\n"
            "蒲剧，又称蒲州梆子，是山西四大梆子中最古老的剧种之一，"
            "2006年被列入第一批国家级非物质文化遗产名录。其唱腔慷慨激越、"
            "粗犷豪放，帽翅功、翎子功等表演特技独树一帜。\n\n"
            f"（system指令摘要：{system[:40]}…；用户请求：{user[:60]}…）\n"
            "配置 ARK_API_KEY 或 ZHIPU_API_KEY 后即可生成真实文案。"
        )


def _make_mock_video(prompt: str) -> Path:
    """生成占位视频：优先 ffmpeg 造2秒实拍感色块视频，无 ffmpeg 则退化为海报图。

    返回临时文件路径（.mp4 或 .png）。
    """
    if shutil.which("ffmpeg"):
        out = Path(tempfile.mkstemp(suffix=".mp4")[1])
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c=0xB23A2E:s=480x270:d=2",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-shortest", "-pix_fmt", "yuv420p", str(out),
            ],
            check=True,
            timeout=60,
        )
        return out
    # 无ffmpeg：退化为海报图（前端视频卡片按扩展名兼容展示）
    out = Path(tempfile.mkstemp(suffix=".png")[1])
    out.write_bytes(_placeholder(f"MOCK VIDEO | {prompt[:50]}", "480x270"))
    return out


class MockVideoProvider(VideoProvider):
    name = "mock（离线·开发测试）"

    def create_video(
        self,
        prompt: str,
        *,
        duration: int = 10,
        resolution: str = "720p",
        ratio: str = "adaptive",
        first_frame: bytes | None = None,
    ) -> str:
        _ = duration, resolution, ratio, first_frame
        return f"mockvid-{int(time.time()*1000)}"

    def poll_video(self, remote_id: str) -> VideoTaskStatus:
        _ = remote_id
        local = _make_mock_video("Puju AIGC mock video")
        return VideoTaskStatus(status="succeeded", local_file=str(local))
