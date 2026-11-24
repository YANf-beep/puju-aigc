"""Pollinations 文生图 Provider（零成本原型兜底）。

无需 API Key，GET 即出图，适合跑通流程与原型演示；
有限流与稳定性风险，正式功能请使用 ark / zhipu。https://pollinations.ai
"""
from __future__ import annotations

import random
from urllib.parse import quote

import requests

from .base import GeneratedImage, ImageProvider


def _parse_size(size: str) -> tuple[int, int]:
    try:
        w, h = size.lower().split("x")
        return max(256, int(w)), max(256, int(h))
    except Exception:
        return 1024, 1024


class PollinationsImageProvider(ImageProvider):
    name = "pollinations（免Key·原型兜底）"

    def text_to_image(
        self, prompt: str, *, size: str = "1024x1024", n: int = 1
    ) -> list[GeneratedImage]:
        w, h = _parse_size(size)
        results: list[GeneratedImage] = []
        for _ in range(max(1, n)):
            seed = random.randint(1, 10**9)  # 不同seed保证多张图有差异
            url = (
                f"https://image.pollinations.ai/prompt/{quote(prompt, safe='')}"
                f"?width={w}&height={h}&seed={seed}&nologo=true"
            )
            resp = requests.get(url, timeout=180)
            resp.raise_for_status()
            results.append(
                GeneratedImage(provider="pollinations", model="flux", data=resp.content)
            )
        return results
