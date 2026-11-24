"""蒲剧领域提示词模板库 —— 双层提示词机制（对应开题报告模块2）。

机制说明：
  第一层「领域模板」：行当、服饰、场景、神态等结构化选项，由模板库保证
      生成内容符合蒲剧剧种规范（专业性）；
  第二层「自由描述」：用户在结构化选项之外自主补充画面细节（个性化），
      对应报告中「创作者自主设定图片细节」的功能要求。

工程约定：本文件先以 Python 字典实现，字段与取值结构与未来数据库
字典表一致，迁移成本低（见 README「下一步开发路线」）。
取值描述可结合素材库与文献持续校订。
"""
from __future__ import annotations

# ---------- 第一层：结构化模板组件 ----------

ROLE_PRESETS: dict[str, str] = {
    "生": "蒲剧生行人物，俊扮，眉目清朗，身着长靠或褶子，仪态端正挺拔",
    "旦": "蒲剧旦行人物，贴片子梳大头，头戴点翠头面，身着女帔或褶子，身段柔美",
    "净": "蒲剧净行人物，勾画脸谱，以红黑为主色的整脸谱式，浓眉凸目，气魄威武",
    "丑": "蒲剧丑行人物，鼻梁勾白粉豆腐块，表情诙谐灵动",
}

COSTUME_PRESETS: dict[str, str] = {
    "蟒袍": "身着绣龙蟒袍，玉带围腰",
    "靠甲": "身扎靠甲，背插四面三角靠旗，英武之气",
    "褶子": "身着素色褶子，简洁利落",
    "女帔": "身着绣花女帔，雍容端丽",
    "箭衣": "身着箭衣，腰系大带，干练洒脱",
}

SCENE_PRESETS: dict[str, str] = {
    "舞台": "传统戏曲舞台，一桌二椅，幕布为底",
    "古戏台": "晋南古戏台上，砖木结构，雕梁画栋",
    "写意": "水墨写意背景，大面积留白，构图雅致",
    "乡野社戏": "晋南乡村社戏场景，热闹质朴",
}

MOOD_PRESETS: dict[str, str] = {
    "威武": "人物气度威武挺拔",
    "柔美": "人物神态柔美含蓄",
    "诙谐": "人物神态诙谐生动",
    "悲怆": "人物神态悲怆激越",
}

QUALITY_SUFFIX = "，中国戏曲艺术风格，工笔重彩，细节精致，构图完整，高清"

# 负向提示词（Seedream等部分模型支持 negative_prompt 字段时使用；
# 不支持的平台可拼入提示词尾部或不使用）
NEGATIVE_PROMPT = "低质量, 模糊, 变形, 畸形手指, 多余肢体, 水印, 文字, 现代服装, 照片写实"


def build_image_prompt(
    role: str = "净",
    costume: str = "蟒袍",
    scene: str = "舞台",
    mood: str = "威武",
    free_text: str = "",
) -> str:
    """双层提示词组装：结构化模板（第一层） + 用户自由描述（第二层）。

    未收录的取值按原文传入（用户自定义的扩展能力）。
    """
    parts = [
        ROLE_PRESETS.get(role, role),
        COSTUME_PRESETS.get(costume, costume),
        SCENE_PRESETS.get(scene, scene),
        MOOD_PRESETS.get(mood, mood),
    ]
    if free_text and free_text.strip():
        parts.append(f"画面细节要求：{free_text.strip()}")
    return "，".join(p for p in parts if p) + QUALITY_SUFFIX


def build_costume_prompt(role: str = "净", free_text: str = "") -> str:
    """照片扮相转换的编辑指令（配合 Seedream 参考图编辑）。"""
    role_desc = ROLE_PRESETS.get(role, role)
    extra = f" {free_text.strip()}" if free_text and free_text.strip() else ""
    return (
        f"将照片中的人物转换为{role_desc}的蒲剧扮相，"
        f"保留人物面部特征与姿态，戏曲装造完整精致，舞台灯光效果{extra}"
    )


def build_video_prompt(
    role: str = "净",
    costume: str = "蟒袍",
    scene: str = "舞台",
    free_text: str = "",
) -> str:
    """短视频生成的双层提示词：领域模板 + 动态描述。"""
    parts = [
        ROLE_PRESETS.get(role, role),
        COSTUME_PRESETS.get(costume, costume),
        SCENE_PRESETS.get(scene, scene),
    ]
    if free_text and free_text.strip():
        parts.append(f"动态与情节要求：{free_text.strip()}")
    return (
        "，".join(p for p in parts if p)
        + "，镜头稳定流畅，人物动作自然连贯，衣袂与靠旗随动作摆动，"
        "中国戏曲艺术风格，高清视频"
    )


COPY_STYLES = ["科普短文", "唱词文案", "剧目介绍", "宣传文案"]

_COPY_STYLE_HINT = {
    "科普短文": "面向普通读者的通俗科普，准确、生动、易读",
    "唱词文案": "符合戏曲唱词的韵律感与文辞风格，可含念白提示",
    "剧目介绍": "介绍剧目背景、剧情梗概与艺术特色",
    "宣传文案": "面向年轻群体的传播文案，活泼有感染力",
}


def build_copy_messages(
    subject: str,
    style: str = "科普短文",
    knowledge: list[str] | None = None,
) -> tuple[str, str]:
    """文案生成的 (system, user) 提示词，knowledge 为 RAG 检索到的领域知识片段。"""
    system = (
        "你是蒲剧（蒲州梆子）文化创作助手，熟悉蒲剧的行当、剧目、唱腔与表演特技。"
        "创作时严格依据给定的领域知识，不得编造史实；涉及蒲剧的内容要体现剧种特色，"
        "区别于京剧、豫剧等其它剧种。"
    )
    style_hint = _COPY_STYLE_HINT.get(style, "内容准确、语言生动")
    blocks = [f"【领域知识{i}】{k}" for i, k in enumerate(knowledge or [], 1)]
    user = f"请围绕主题「{subject}」创作一段蒲剧{style}。"
    if blocks:
        user += "\n\n参考以下领域知识（不得与之矛盾）：\n" + "\n".join(blocks)
    user += f"\n\n要求：{style_hint}，篇幅300字左右。"
    return system, user
