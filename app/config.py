"""全局配置：从环境变量 / .env 读取。

安全约定：密钥只放后端（.env 或部署平台的 Secrets），
严禁写入代码、提交仓库或出现在前端。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------- 火山引擎方舟（主路线） ----------
ARK_API_KEY = os.getenv("ARK_API_KEY", "").strip()
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
# 模型ID带日期后缀：须与方舟控制台「开通管理」页一致，且对应模型已开通
ARK_LLM_MODEL = os.getenv("ARK_LLM_MODEL", "doubao-seed-2-0-lite-260428")
ARK_T2I_MODEL = os.getenv("ARK_T2I_MODEL", "doubao-seedream-5-0-260128")
# 扮相转换：SeedEdit专用模型已下线，编辑由Seedream参考图能力实现，默认同T2I模型
ARK_I2I_MODEL = os.getenv("ARK_I2I_MODEL", "doubao-seedream-5-0-260128")
# 视频生成（Seedance，需在方舟控制台开通；mini为最便宜档）
ARK_VIDEO_MODEL = os.getenv("ARK_VIDEO_MODEL", "doubao-seedance-2-0-mini-260615")

# ---------- 硅基流动 SiliconFlow（低价视频路线） ----------
# 注册 https://cloud.siliconflow.cn → API密钥；新用户赠送额度可生成数十条视频
# 注意：文生视频与图生视频是两个模型，分别在下面配置
SF_API_KEY = os.getenv("SF_API_KEY", "").strip()
SF_BASE_URL = os.getenv("SF_BASE_URL", "https://api.siliconflow.cn").rstrip("/")
SF_VIDEO_MODEL = os.getenv("SF_VIDEO_MODEL", "Wan-AI/Wan2.2-T2V-A14B")       # 文生视频
SF_VIDEO_I2V_MODEL = os.getenv("SF_VIDEO_I2V_MODEL", "Wan-AI/Wan2.2-I2V-A14B")  # 图生视频（首帧）

# ---------- 智谱开放平台（免费备用） ----------
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "").strip()
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
ZHIPU_LLM_MODEL = os.getenv("ZHIPU_LLM_MODEL", "glm-4-flash")
ZHIPU_T2I_MODEL = os.getenv("ZHIPU_T2I_MODEL", "cogview-3-flash")

# ---------- 服务选择（多模型适配层入口） ----------
# 图像: ark | zhipu | pollinations | mock    文本: ark | zhipu | mock    视频: ark | mock
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "ark").strip().lower()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ark").strip().lower()
VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "ark").strip().lower()

# ---------- 其他 ----------
KNOWLEDGE_FILE = BASE_DIR / "data" / "knowledge" / "puju_knowledge.json"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "").strip()

# ---------- 数据库（开发期SQLite零配置；部署切MySQL只需改此连接串） ----------
# 例: mysql+pymysql://user:password@localhost:3306/puju?charset=utf8mb4
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'data' / 'puju.db').as_posix()}"
)

# ---------- 用户会话 ----------
# 生产环境务必在 .env 中设置随机 SECRET_KEY（如 python -c "import secrets;print(secrets.token_hex(32))"）
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
TOKEN_EXPIRE_DAYS = int(os.getenv("TOKEN_EXPIRE_DAYS", "7"))

# ---------- 生成作品文件存储（数据库只存路径，不存媒体本体） ----------
WORKS_DIR = Path(os.getenv("WORKS_DIR", str(BASE_DIR / "data" / "works")))
WORKS_DIR.mkdir(parents=True, exist_ok=True)

# 任务结果媒体（未保存到广场的生成结果，任务中心展示用）
TASK_MEDIA_DIR = BASE_DIR / "data" / "task_media"
TASK_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# 科普知识配图/视频（AI生成封面 + 用户上传）
KNOWLEDGE_MEDIA_DIR = BASE_DIR / "data" / "knowledge_media"
KNOWLEDGE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# 上传大小限制（科普素材）
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))

# ---------- 前端构建产物（Vue3 dist，存在则由后端直接托管为完整网站） ----------
WEB_DIST_DIR = BASE_DIR / "puju-web" / "dist"


class ConfigError(RuntimeError):
    """配置缺失（如未填写 API Key）。"""


def require_key(name: str, value: str, alternative: str) -> str:
    """校验必填密钥，缺失时给出可操作的中文提示。"""
    if not value:
        raise ConfigError(
            f"未配置 {name}。请在项目根目录 .env 中填写（参考 .env.example），"
            f"或临时改用 {alternative}。"
        )
    return value
