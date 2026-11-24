"""硅基流动 SiliconFlow 视频生成 Provider（Wan2.2，走注册赠送额度）。

定位：低成本视频路线（对应"多模型服务适配"设计）。

- 注册 https://cloud.siliconflow.cn（手机号）→「API密钥」创建；
  Wan2.2 按条计费，从注册赠送的额度中扣（约几毛/条，可生成数十条）；
- 接口为异步任务式（已实测验证）：
  POST /v1/video/submit 提交 → POST /v1/video/status 轮询（JSON体带 requestId）；
- 限制：固定约5秒、无音频、生成约需2~5分钟；需要10秒/更高画质请切 ark（Seedance）；
- 文生视频（T2V）与图生视频（I2V首帧）是两个模型，按是否上传首帧自动切换。
"""
from __future__ import annotations

import base64

import requests

from .. import config
from .base import VideoProvider, VideoTaskStatus

TIMEOUT = 60

_STATUS_MAP = {
    "succeed": "succeeded",
    "succeeded": "succeeded",
    "success": "succeeded",
    "inprogress": "running",
    "in_progress": "running",
    "processing": "running",
    "queued": "pending",
    "failed": "failed",
}


def _check(resp: requests.Response) -> dict:
    if resp.status_code == 401:
        raise PermissionError(
            "硅基流动 API Key 无效或未填写（SF_API_KEY）。请到 cloud.siliconflow.cn"
            "「API密钥」页创建并填入 .env。"
        )
    if resp.status_code == 429:
        raise RuntimeError("请求过于频繁或并发超限（429），请稍后重试。")
    resp.raise_for_status()
    return resp.json()


class SiliconFlowVideoProvider(VideoProvider):
    name = "siliconflow（Wan2.2·视频）"

    def __init__(self) -> None:
        config.require_key(
            "SF_API_KEY", config.SF_API_KEY, "VIDEO_PROVIDER=mock（离线）或 ark（火山）"
        )
        self.api_key = config.SF_API_KEY
        self.base = config.SF_BASE_URL
        self.t2v_model = config.SF_VIDEO_MODEL
        self.i2v_model = config.SF_VIDEO_I2V_MODEL
        self.video_model = self.t2v_model  # 展示用

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def create_video(
        self,
        prompt: str,
        *,
        duration: int = 5,
        resolution: str = "480p",
        ratio: str = "adaptive",
        first_frame: bytes | None = None,
    ) -> str:
        # 文生/图生是两个模型：上传首帧时自动切换 I2V
        payload: dict = {
            "model": self.i2v_model if first_frame else self.t2v_model,
            "prompt": prompt,
        }
        if first_frame:
            data_uri = "data:image/png;base64," + base64.b64encode(first_frame).decode()
            payload["image"] = data_uri  # 图生视频：首帧参考
        data = _check(
            requests.post(
                f"{self.base}/v1/video/submit",
                headers=self._headers(),
                json=payload,
                timeout=TIMEOUT,
            )
        )
        request_id = data.get("requestId")
        if not request_id:
            raise RuntimeError(f"视频任务提交失败：{str(data)[:200]}")
        return request_id

    def poll_video(self, remote_id: str) -> VideoTaskStatus:
        # 实测：状态查询为 POST /v1/video/status（JSON体带 requestId）
        data = _check(
            requests.post(
                f"{self.base}/v1/video/status",
                headers=self._headers(),
                json={"requestId": remote_id},
                timeout=TIMEOUT,
            )
        )
        raw = str(data.get("status", "")).lower()
        status = _STATUS_MAP.get(raw, raw)

        video_url = None
        videos = ((data.get("results") or {}).get("videos")) or []
        if videos:
            video_url = videos[0].get("url")

        error = None
        if status == "failed":
            error = str(data.get("reason") or data.get("message") or data)[:200]
        if status == "succeeded" and not video_url:
            status = "failed"
            error = "任务成功但未返回视频URL"

        return VideoTaskStatus(status=status, video_url=video_url, error=error)
