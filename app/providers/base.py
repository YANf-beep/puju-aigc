"""Provider 抽象接口（多模型服务适配层）。

对应开题报告模块2/模块3：上层业务（FastAPI 接口、Streamlit 演示）只依赖
本抽象，不直接耦合任何具体平台；接入新平台只需实现 ImageProvider /
LLMProvider 并在 providers/__init__.py 的工厂注册，即可通过配置切换。
这层设计即论文中「多模型服务适配层」，也是答辩时回应
「调API的技术含量」质疑的落点之一。
"""
from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GeneratedImage:
    """统一图像结果：url 与 data 至少一项非空。"""

    provider: str
    model: str
    url: str | None = None
    data: bytes | None = None

    def as_dict(self) -> dict:
        """序列化（FastAPI 任务结果 / Streamlit 展示用）。"""
        d = {"provider": self.provider, "model": self.model, "url": self.url}
        if self.data:
            d["image_base64"] = base64.b64encode(self.data).decode()
        return d


class ImageProvider(ABC):
    """图像生成服务接口（文生图 + 图像编辑）。"""

    name: str = "base"

    @abstractmethod
    def text_to_image(
        self, prompt: str, *, size: str = "1024x1024", n: int = 1
    ) -> list[GeneratedImage]:
        """文生图：prompt 为拼接完成的完整提示词（双层提示词机制的产物）。"""

    def edit_image(
        self, image: bytes, prompt: str, **kwargs
    ) -> list[GeneratedImage]:
        """图生图 / 图像编辑（照片扮相转换）。默认不支持。"""
        raise NotImplementedError(
            f"当前图像服务 [{self.name}] 不支持图像编辑（扮相转换）。"
            f"扮相转换依赖火山引擎方舟的 SeedEdit 接口，请在侧栏/配置中切换到 ark。"
        )

    @property
    def supports_edit(self) -> bool:
        """子类覆写了 edit_image 即视为支持编辑。"""
        return type(self).edit_image is not ImageProvider.edit_image


class LLMProvider(ABC):
    """文本生成服务接口。"""

    name: str = "base"

    @abstractmethod
    def chat(
        self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        """对话式文本生成（戏曲文案 / 剧目介绍）。"""


@dataclass
class VideoTaskStatus:
    """视频异步任务状态（平台侧）。"""

    status: str  # queued | running | succeeded | failed
    video_url: str | None = None   # 生成完成后的视频下载地址
    local_file: str | None = None  # mock等本地模式直接给出文件路径
    error: str | None = None


class VideoProvider(ABC):
    """视频生成服务接口（Seedance 等，异步任务式：提交 → 轮询）。"""

    name: str = "base"

    @abstractmethod
    def create_video(
        self,
        prompt: str,
        *,
        duration: int = 10,
        resolution: str = "720p",
        ratio: str = "adaptive",
        first_frame: bytes | None = None,
    ) -> str:
        """提交文生视频/图生视频任务，返回平台任务ID。"""

    @abstractmethod
    def poll_video(self, remote_id: str) -> VideoTaskStatus:
        """查询视频任务状态。"""
