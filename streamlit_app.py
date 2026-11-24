"""蒲剧数字活化平台 · AI创作演示（Streamlit，跨设备演示用）。

复用与 FastAPI 完全相同的核心（providers / prompts / rag），
用于开发验证、中期检查与跨设备演示——正式平台前端仍为 Vue3（见开题报告）。

运行：
    streamlit run streamlit_app.py                                # 本机
    streamlit run streamlit_app.py --server.address 0.0.0.0 \
        --server.port 8501 --server.headless true                 # 局域网演示
公网部署（Streamlit Community Cloud）见 README，务必设置 DEMO_PASSWORD。
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 确保 app 包可导入

from app import config  # noqa: E402
from app.config import ConfigError  # noqa: E402
from app.prompts import opera_templates as T  # noqa: E402
from app.rag import knowledge as rag  # noqa: E402
from app.providers import (  # noqa: E402
    get_image_provider,
    get_llm_provider,
    image_provider_options,
    llm_provider_options,
)

st.set_page_config(page_title="蒲剧数字活化平台 · AI创作演示", page_icon="🎭", layout="wide")

# ---------------- 演示密码门（公网部署时保护免费额度） ----------------
if config.DEMO_PASSWORD:
    pwd = st.text_input("演示访问密码", type="password")
    if pwd != config.DEMO_PASSWORD:
        st.warning("请输入演示密码（见 .env / 云端 Secrets 中的 DEMO_PASSWORD）")
        st.stop()

st.title("🎭 蒲剧数字活化平台 · AI创作演示")
st.caption(
    "双层提示词机制（领域模板 + 自由描述）· 轻量RAG知识注入 · 多模型服务适配层"
    " —— 对应开题报告模块2/3；正式平台前端为 Vue3，本页为开发验证与演示原型。"
)

# ---------------- 侧栏：多模型服务切换（适配层演示） ----------------
def _provider_status(getter, name: str) -> tuple[bool, str]:
    """探测服务可用性（Key是否配置等），返回 (可用, 提示)。"""
    try:
        getter(name)
        return True, ""
    except ConfigError as e:
        return False, str(e)
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


with st.sidebar:
    st.header("⚙️ 生成服务（可切换）")
    img_opts = image_provider_options()
    img_default = config.IMAGE_PROVIDER if config.IMAGE_PROVIDER in img_opts else "mock"
    img_choice = st.selectbox(
        "图像服务",
        img_opts,
        index=img_opts.index(img_default),
        help="多模型服务适配层：ark=火山引擎(主路线)，zhipu=智谱(免费备用)，"
             "pollinations=免Key(原型兜底)，mock=离线测试",
    )
    ok, msg = _provider_status(get_image_provider, img_choice)
    st.caption("✅ 已就绪" if ok else f"⚠️ {msg}")

    llm_opts = llm_provider_options()
    llm_default = config.LLM_PROVIDER if config.LLM_PROVIDER in llm_opts else "mock"
    llm_choice = st.selectbox("文本服务", llm_opts, index=llm_opts.index(llm_default))
    ok2, msg2 = _provider_status(get_llm_provider, llm_choice)
    st.caption("✅ 已就绪" if ok2 else f"⚠️ {msg2}")

    st.divider()
    st.caption("密钥只在后端 .env / 云端 Secrets 中配置，本页面不接触任何Key。")


# ---------------- 图片结果展示（各页签复用） ----------------
def _display_images(images, key_prefix: str) -> None:
    if not images:
        st.warning("服务未返回图像。")
        return
    cols = st.columns(min(len(images), 2))
    for i, g in enumerate(images):
        with cols[i % len(cols)]:
            if g.data:
                st.image(g.data, caption=f"{g.provider} · {g.model}")
                st.download_button(
                    "⬇️ 下载", g.data, file_name=f"puju_{i + 1}.png",
                    key=f"{key_prefix}_dl{i}",
                )
            elif g.url:
                st.image(g.url, caption=f"{g.provider} · {g.model}")
                st.markdown(f"[查看原图]({g.url})")


# ---------------- 页签一：戏曲插画生成 ----------------
def tab_image_generation() -> None:
    left, right = st.columns([1, 2])
    with left:
        st.subheader("第一层 · 领域模板")
        role = st.selectbox("行当", list(T.ROLE_PRESETS.keys()), index=2)
        costume = st.selectbox("服饰", list(T.COSTUME_PRESETS.keys()))
        scene = st.selectbox("场景", list(T.SCENE_PRESETS.keys()))
        mood = st.selectbox("神态", list(T.MOOD_PRESETS.keys()))
        st.subheader("第二层 · 自由描述（创作者自设细节）")
        free_text = st.text_area(
            "画面细节",
            placeholder="例：手持马鞭做勒马式，目光炯炯，戏台楹联隐约可见",
            height=90,
        )
        col_a, col_b = st.columns(2)
        size = col_a.selectbox("尺寸", ["1024x1024", "1280x720", "1440x720"])
        n = col_b.slider("生成数量", 1, 4, 1)
        prompt = T.build_image_prompt(role, costume, scene, mood, free_text)
        with st.expander("查看最终提示词（双层提示词机制）"):
            st.code(prompt, language=None)
            st.caption(f"负向提示词（支持的模型生效）：{T.NEGATIVE_PROMPT}")
        if st.button("🎨 生成戏曲插画", type="primary", use_container_width=True):
            with st.spinner("生成中，通常需要几秒到几十秒…"):
                try:
                    prov = get_image_provider(img_choice)
                    images = prov.text_to_image(prompt, size=size, n=n)
                    st.session_state["last_images"] = images
                except Exception as e:  # noqa: BLE001
                    st.error(f"生成失败：{e}")
    with right:
        st.subheader("生成结果")
        images = st.session_state.get("last_images")
        if images:
            _display_images(images, key_prefix="t1")
            if st.button("清除结果", key="t1_clear"):
                st.session_state.pop("last_images", None)
                st.rerun()
        else:
            st.info("在左侧选择行当、服饰等结构化选项、补充自由描述后点击生成，结果将显示在这里。")


# ---------------- 页签二：照片扮相转换 ----------------
def tab_costume_transfer() -> None:
    st.subheader("照片扮相转换（SeedEdit 图像编辑）")
    st.caption("上传照片 → 选择行当 → 生成符合蒲剧行当规范的扮相形象，保留人物面部特征与姿态。")
    try:
        prov = get_image_provider(img_choice)
    except ConfigError as e:
        st.warning(f"当前图像服务不可用：{e}")
        prov = None
    if prov is not None and not prov.supports_edit:
        st.warning(
            f"当前图像服务 [{prov.name}] 不支持图像编辑，扮相转换需切换到 "
            f"**ark（火山引擎 SeedEdit）**——请在左侧边栏切换。"
        )
    uploaded = st.file_uploader("上传照片", type=["png", "jpg", "jpeg", "webp"])
    c1, c2, c3 = st.columns(3)
    role = c1.selectbox("目标行当", list(T.ROLE_PRESETS.keys()), index=2, key="c_role")
    free_text = c2.text_input("补充细节（可选）", placeholder="例：红色大靠，叉腰立正式")
    scale = c3.selectbox("输出放大倍数", [1, 2], index=0)
    prompt = T.build_costume_prompt(role, free_text)
    with st.expander("查看编辑指令"):
        st.code(prompt, language=None)
    can_run = uploaded is not None and prov is not None
    if st.button("🎭 生成扮相", type="primary", disabled=not can_run):
        image_bytes = uploaded.getvalue()
        st.markdown("**编辑前 / 编辑后**")
        col1, col2 = st.columns(2)
        col1.image(image_bytes, caption="原图")
        with st.spinner("扮相转换中…"):
            try:
                results = prov.edit_image(image_bytes, prompt, scale=scale or None)
            except Exception as e:  # noqa: BLE001
                col2.error(f"转换失败：{e}")
                return
        with col2:
            _display_images(results, key_prefix="t2")


# ---------------- 页签三：戏曲文案生成 ----------------
def tab_copywriting() -> None:
    st.subheader("戏曲文案生成（RAG 知识注入）")
    subject = st.text_input(
        "主题", value="蒲剧《挂画》的艺术特色", placeholder="例：蒲剧脸谱的颜色寓意"
    )
    style = st.selectbox("文体", T.COPY_STYLES)
    use_rag = st.checkbox("启用领域知识库检索（RAG）", value=True)
    knowledge_snippets: list[str] = []
    if use_rag and subject:
        hits = rag.retrieve(subject, k=3)
        knowledge_snippets = rag.format_snippets(hits)
        with st.expander(f"📚 检索到的领域知识（{len(hits)}条，将注入提示词）"):
            for h in hits:
                st.caption(f"**{h['title']}**（相关度 {h['score']}）\n\n{h['text']}")
    if st.button("✍️ 生成文案", type="primary"):
        system, user = T.build_copy_messages(subject, style, knowledge_snippets)
        with st.expander("查看完整提示词（system + user）"):
            st.code(f"[system]\n{system}\n\n[user]\n{user}", language=None)
        with st.spinner("生成中…"):
            try:
                prov = get_llm_provider(llm_choice)
                text = prov.chat(system, user, temperature=0.7, max_tokens=1024)
            except Exception as e:  # noqa: BLE001
                st.error(f"生成失败：{e}")
                return
        st.markdown("---")
        st.markdown(text)
        st.code(text, language=None)  # 便于复制


# ---------------- 主流程 ----------------
tab1, tab2, tab3 = st.tabs(["🖼️ 戏曲插画生成", "👤 照片扮相转换", "✍️ 戏曲文案生成"])
with tab1:
    tab_image_generation()
with tab2:
    tab_costume_transfer()
with tab3:
    tab_copywriting()

st.divider()
st.caption(
    "蒲剧数字活化平台 · AI能力演示原型 | 数据与素材仅用于学术研究 | "
    "AI生成内容已在平台设计中按国家相关规定添加标识"
)
