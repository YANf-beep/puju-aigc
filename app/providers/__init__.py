"""Provider 工厂：按名称实例化服务，未指定时读 .env 默认值。

上层用法：
    from app.providers import get_image_provider, get_llm_provider
    img_provider = get_image_provider()          # 用 .env 默认
    img_provider = get_image_provider("zhipu")   # 临时切换（Streamlit侧栏/接口参数）
"""
from __future__ import annotations

from .. import config
from ..config import ConfigError
from . import ark, mock, pollinations, siliconflow, zhipu
from .base import (
    GeneratedImage,
    ImageProvider,
    LLMProvider,
    VideoProvider,
    VideoTaskStatus,
)

_IMAGE_REGISTRY: dict[str, type[ImageProvider]] = {
    "ark": ark.ArkImageProvider,
    "zhipu": zhipu.ZhipuImageProvider,
    "pollinations": pollinations.PollinationsImageProvider,
    "mock": mock.MockImageProvider,
}

_LLM_REGISTRY: dict[str, type[LLMProvider]] = {
    "ark": ark.ArkLLMProvider,
    "zhipu": zhipu.ZhipuLLMProvider,
    "mock": mock.MockLLMProvider,
}

_VIDEO_REGISTRY: dict[str, type[VideoProvider]] = {
    "ark": ark.ArkVideoProvider,
    "siliconflow": siliconflow.SiliconFlowVideoProvider,
    "mock": mock.MockVideoProvider,
}


def get_image_provider(name: str | None = None) -> ImageProvider:
    key = (name or config.IMAGE_PROVIDER).strip().lower()
    if key not in _IMAGE_REGISTRY:
        raise ConfigError(f"未知图像服务 '{key}'，可选：{list(_IMAGE_REGISTRY)}")
    return _IMAGE_REGISTRY[key]()


def get_llm_provider(name: str | None = None) -> LLMProvider:
    key = (name or config.LLM_PROVIDER).strip().lower()
    if key not in _LLM_REGISTRY:
        raise ConfigError(f"未知文本服务 '{key}'，可选：{list(_LLM_REGISTRY)}")
    return _LLM_REGISTRY[key]()


def get_video_provider(name: str | None = None) -> VideoProvider:
    key = (name or config.VIDEO_PROVIDER).strip().lower()
    if key not in _VIDEO_REGISTRY:
        raise ConfigError(f"未知视频服务 '{key}'，可选：{list(_VIDEO_REGISTRY)}")
    return _VIDEO_REGISTRY[key]()


def video_provider_options() -> list[str]:
    return list(_VIDEO_REGISTRY)


def image_provider_options() -> list[str]:
    return list(_IMAGE_REGISTRY)


def llm_provider_options() -> list[str]:
    return list(_LLM_REGISTRY)
