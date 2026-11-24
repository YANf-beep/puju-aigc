"""智谱开放平台 Provider（免费备用路线）。

GLM-4-Flash（文本）与 CogView-3-Flash（文生图）为免费档模型，
接口与 OpenAI 协议兼容。https://open.bigmodel.cn

注意：智谱不提供图像编辑接口——扮相转换请使用 ark（SeedEdit）。
"""
from __future__ import annotations

import requests

from .. import config
from .base import GeneratedImage, ImageProvider, LLMProvider

TIMEOUT = 120


def _check(resp: requests.Response) -> dict:
    if resp.status_code == 401:
        raise PermissionError("智谱 API Key 无效或未填写（ZHIPU_API_KEY），请到 open.bigmodel.cn 获取。")
    if resp.status_code == 429:
        raise RuntimeError("请求过于频繁或免费额度受限（429），请稍后重试。")
    resp.raise_for_status()
    return resp.json()


class ZhipuImageProvider(ImageProvider):
    """CogView-3-Flash 文生图（免费档）。"""

    name = "zhipu（智谱·免费备用）"

    def __init__(self) -> None:
        config.require_key(
            "ZHIPU_API_KEY", config.ZHIPU_API_KEY,
            "IMAGE_PROVIDER=pollinations（免Key）或 mock（离线）",
        )
        self.api_key = config.ZHIPU_API_KEY
        self.base = config.ZHIPU_BASE_URL
        self.t2i_model = config.ZHIPU_T2I_MODEL

    def text_to_image(
        self, prompt: str, *, size: str = "1024x1024", n: int = 1
    ) -> list[GeneratedImage]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        results: list[GeneratedImage] = []
        for _ in range(max(1, n)):
            data = _check(
                requests.post(
                    f"{self.base}/images/generations",
                    headers=headers,
                    json={"model": self.t2i_model, "prompt": prompt, "size": size},
                    timeout=TIMEOUT,
                )
            )
            for item in data.get("data", []):
                results.append(
                    GeneratedImage(
                        provider="zhipu", model=self.t2i_model, url=item.get("url")
                    )
                )
        if not results:
            raise RuntimeError(f"智谱未返回图像结果：{str(data)[:200]}")
        return results


class ZhipuLLMProvider(LLMProvider):
    """GLM-4-Flash（免费档）。"""

    name = "zhipu（GLM-4-Flash·免费备用）"

    def __init__(self) -> None:
        config.require_key(
            "ZHIPU_API_KEY", config.ZHIPU_API_KEY, "LLM_PROVIDER=mock（离线）"
        )
        self.api_key = config.ZHIPU_API_KEY
        self.base = config.ZHIPU_BASE_URL
        self.llm_model = config.ZHIPU_LLM_MODEL

    def chat(
        self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _check(
            requests.post(
                f"{self.base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60,
            )
        )
        return data["choices"][0]["message"]["content"]
