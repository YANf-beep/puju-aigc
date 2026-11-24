"""火山引擎方舟 Provider（主路线，对应开题报告技术途径）。

全部使用 HTTP REST（requests）调用，不依赖官方SDK —— 方舟的对话接口与
OpenAI 协议兼容，图像接口为方舟自有形态：

  - 文本生成 : POST {base}/chat/completions      （豆包/GLM/DeepSeek等）
  - 文生图   : POST {base}/images/generations    （Seedream 系列）
  - 图像编辑 : 同上接口，传入参考图 image 字段    （Seedream 4.0+ 原生编辑能力）

官方文档：https://www.volcengine.com/docs/82379
⚠ 注意：
  1. 模型ID带日期后缀，且必须已在方舟控制台「开通管理」页开通
     （未开通会返回 ModelNotOpen 404 错误）；
  2. 原 SeedEdit 专用模型（doubao-seededit-3-0-i2i-250628）已下线，
     扮相转换现通过 Seedream 参考图编辑实现。
"""
from __future__ import annotations

import base64

import requests

from .. import config
from .base import GeneratedImage, ImageProvider, LLMProvider, VideoProvider, VideoTaskStatus

TIMEOUT = 180  # 图像生成耗时较长，超时给足


def _check(resp: requests.Response) -> dict:
    """统一响应检查，常见错误翻译成可操作的中文提示。"""
    if resp.status_code == 401:
        raise PermissionError(
            "方舟 API Key 无效或未填写（ARK_API_KEY）。请到方舟控制台"
            "「API Key管理」创建并填入 .env。"
        )
    if resp.status_code == 404:
        err_code = ""
        try:
            err_code = resp.json().get("error", {}).get("code", "")
        except Exception:  # noqa: BLE001
            pass
        if err_code == "ModelNotOpen":
            raise ValueError(
                "模型未开通——请到方舟控制台「开通管理」页，搜索并开通对应模型"
                "（开通免费、按量计费），然后重试：https://console.volcengine.com/ark"
            )
        raise ValueError(
            f"模型或接口不存在（404）。请核对 .env 中的模型ID与方舟控制台"
            f"「开通管理」页显示的完全一致。返回内容：{resp.text[:200]}"
        )
    if resp.status_code == 429:
        raise RuntimeError("请求过于频繁或额度不足（429）。请稍后重试，或到控制台查看额度。")
    resp.raise_for_status()
    return resp.json()


class ArkImageProvider(ImageProvider):
    """Seedream 文生图 + SeedEdit 图像编辑。"""

    name = "ark（火山引擎·主路线）"

    def __init__(self) -> None:
        config.require_key(
            "ARK_API_KEY", config.ARK_API_KEY,
            "IMAGE_PROVIDER=pollinations（免费原型）或 IMAGE_PROVIDER=mock（离线）",
        )
        self.api_key = config.ARK_API_KEY
        self.base = config.ARK_BASE_URL
        self.t2i_model = config.ARK_T2I_MODEL
        self.i2i_model = config.ARK_I2I_MODEL

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _post_images(self, payload: dict) -> dict:
        return _check(
            requests.post(
                f"{self.base}/images/generations",
                headers=self._headers(),
                json=payload,
                timeout=TIMEOUT,
            )
        )

    def text_to_image(
        self, prompt: str, *, size: str = "2K", n: int = 1
    ) -> list[GeneratedImage]:
        payload = {
            "model": self.t2i_model,
            "prompt": prompt,
            "size": size,            # Seedream 5.x 用 1K/2K/4K；旧版用 1024x1024
            "response_format": "url",
            # 按《人工智能生成合成内容标识办法》要求保留AI标识
            "watermark": True,
        }
        results: list[GeneratedImage] = []
        # 逐张生成（n 次）；如遇尺寸等参数不兼容，自动回退到通用参数重试
        for _ in range(max(1, n)):
            try:
                data = self._post_images(payload)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 400:
                    fallback = dict(payload, size="2K")
                    fallback.pop("watermark", None)
                    data = self._post_images(fallback)
                else:
                    raise
            for item in data.get("data", []):
                results.append(
                    GeneratedImage(
                        provider="ark", model=self.t2i_model, url=item.get("url")
                    )
                )
        if not results:
            raise RuntimeError(f"方舟未返回图像结果：{str(data)[:200]}")
        return results

    def edit_image(self, image: bytes, prompt: str, **kwargs) -> list[GeneratedImage]:
        """照片扮相转换：基于参考图的指令式编辑。

        原 SeedEdit 专用模型已下线，当前通过 images/generations 接口传入
        参考图（image 字段，base64数据URI）实现，由 Seedream 4.0+ 完成
        「保留人物特征 + 按指令重绘扮相」的编辑任务（参数形态已实测验证）。
        """
        data_uri = "data:image/png;base64," + base64.b64encode(image).decode()
        payload = {
            "model": self.i2i_model,
            "prompt": prompt,
            "image": [data_uri],
        }
        data = self._post_images(payload)
        return [
            GeneratedImage(provider="ark", model=self.i2i_model, url=item.get("url"))
            for item in data.get("data", [])
        ]


class ArkLLMProvider(LLMProvider):
    """豆包大模型（对话接口与 OpenAI 协议兼容）。"""

    name = "ark（豆包大模型）"

    def __init__(self) -> None:
        config.require_key(
            "ARK_API_KEY", config.ARK_API_KEY, "LLM_PROVIDER=zhipu（免费）或 mock（离线）"
        )
        self.api_key = config.ARK_API_KEY
        self.base = config.ARK_BASE_URL
        self.llm_model = config.ARK_LLM_MODEL

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


class ArkVideoProvider(VideoProvider):
    """Seedance 视频生成（异步任务式：提交 /contents/generations/tasks → 轮询）。

    接口形态按方舟文档实现；若与控制台最新文档有出入，仅调整本类即可。
    ⚠ 需先在方舟控制台「开通管理」页开通对应 Seedance 模型。
    """

    name = "ark（Seedance视频）"

    def __init__(self) -> None:
        config.require_key(
            "ARK_API_KEY", config.ARK_API_KEY, "VIDEO_PROVIDER=mock（离线）"
        )
        self.api_key = config.ARK_API_KEY
        self.base = config.ARK_BASE_URL
        self.video_model = config.ARK_VIDEO_MODEL

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def create_video(
        self,
        prompt: str,
        *,
        duration: int = 10,
        resolution: str = "720p",
        ratio: str = "adaptive",
        first_frame: bytes | None = None,
    ) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        if first_frame:
            data_uri = "data:image/png;base64," + base64.b64encode(first_frame).decode()
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": data_uri},
                    "role": "first_frame",  # 图生视频：以上传图为首帧
                }
            )
        payload = {
            "model": self.video_model,
            "content": content,
            "duration": duration,        # 5 | 10 秒
            "resolution": resolution,    # 720p | 1080p
            "ratio": ratio,              # adaptive | 16:9 | 9:16 | 1:1
        }
        data = _check(
            requests.post(
                f"{self.base}/contents/generations/tasks",
                headers=self._headers(),
                json=payload,
                timeout=60,
            )
        )
        return data["id"]

    def poll_video(self, remote_id: str) -> VideoTaskStatus:
        data = _check(
            requests.get(
                f"{self.base}/contents/generations/tasks/{remote_id}",
                headers=self._headers(),
                timeout=30,
            )
        )
        status = str(data.get("status", "")).lower()
        video_url = (data.get("content") or {}).get("video_url")
        error = None
        if status == "failed":
            error = str(data.get("error") or data)[:200] or "视频生成失败"
        return VideoTaskStatus(
            status=status, video_url=video_url, error=error
        )
