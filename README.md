# 蒲剧数字活化平台（puju-aigc）

毕业设计《基于多模态AIGC的地方传统戏曲数字活化平台设计与实现》的可运行实现，对应开题报告**模块1（素材库）、模块2（提示词工程与参数化细节控制）、模块3（平台设计与实现）**。

**当前形态已是完整网站**：Vue3 + Element Plus 前端（戏曲科普首页 / 作品广场 / AI创作台 / 我的作品 / 手机号注册登录）、FastAPI 后端（JWT认证、**持久化任务队列（刷新/关页/重启不丢，多任务并行）**、作品点赞互动、知识库富媒体）、多模型服务适配层（火山引擎：豆包对话 / Seedream图像 / **Seedance视频**）、轻量RAG。**dist 已预构建，无需 Node 即可运行。**

## 核心功能

- **戏曲科普首页**：12条蒲剧知识配AI生成封面 + B站视频直达链接 + 素材上传接口（`POST /api/knowledge/{id}/media`，png/jpg/mp4）
- **AI创作台四件套**：戏曲插画 / 照片扮相转换 / **短视频（5/10秒，文生视频+图生视频首帧）** / 戏曲文案（RAG注入）
- **任务中心**（顶栏铃铛）：任务落库持久化，关闭网页、重启电脑后回来仍在；多创作并行；完成后一键保存到广场
- **手机号注册登录**（手机号+密码，JWT）
- **作品广场**：图像/视频/文案三类作品，点赞、我的作品管理、AI生成标识

## 架构

```
┌─ Vue3 + Element Plus（puju-web/，构建产物 dist/ 由后端托管）─┐
│  作品广场 · AI创作台(插画/扮相/文案) · 戏曲科普 · 我的作品     │
│              ↑ HTTP /api（开发经vite代理，生产同源）          │
│   FastAPI  app/api/                                          │
│   ├─ 认证 auth.py（JWT注册登录）  ├─ 互动 works.py（广场/点赞）│
│   ├─ 知识库 knowledge.py          ├─ 异步任务 tasks.py        │
│   ├─ db.py（SQLAlchemy：SQLite开发/MySQL可切）                │
│   ├─ 双层提示词 app/prompts/（领域模板+自由描述）             │
│   ├─ 轻量RAG app/rag/ + data/knowledge/                      │
│   └─ 多模型适配层 app/providers/                              │
│        ├─ ark          火山引擎（Seedream文生图/SeedEdit编辑/豆包LLM，主路线）
│        ├─ zhipu        智谱（GLM-4-Flash/CogView-3-Flash，免费备用）
│        ├─ pollinations 免Key文生图（原型兜底）                 │
│        └─ mock         离线Mock（零Key跑通全流程）             │
└─ 另附 Streamlit 演示页 streamlit_app.py（快速验证用）─────────┘
```

## 快速开始

### 模式A：一条命令启动完整网站（演示/答辩首选）

**最简单（macOS）**：在项目文件夹双击 **`启动网站.command`** —— 首次自动安装依赖（1~3分钟），随后自动打开浏览器。`.env` 已预置为离线Mock模式，无需任何Key。

**手动方式（任意系统）**：

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
# 未配置Key时默认可用 mock 体验全部功能；配置Key后自动切换真实生成
uvicorn app.api.main:app --port 8000
```

浏览器打开 **http://localhost:8000** —— 注册 → AI创作台生成 → 保存到作品广场 → 点赞，全流程可走通。

**跨设备/局域网演示**（需要时）：启动命令加 `--host 0.0.0.0`，同一WiFi下其他设备访问 `http://<你的内网IP>:8000`；macOS 首次会弹防火墙提示，点「允许」即可。

### 模式B：前后端分离开发（改前端代码时用）

```bash
# 终端1：后端
uvicorn app.api.main:app --reload --port 8000
# 终端2：前端（vite代理已配置，无跨域问题）
cd puju-web && npm install && npm run dev
# 打开 http://localhost:5173
```

修改前端后重新构建：`cd puju-web && npm run build`（产物自动被后端托管）。

### 模式C：Streamlit 快速演示（保留）

```bash
streamlit run streamlit_app.py
```

## 密钥与免费额度

| 平台 | 获取方式 | 免费情况 |
|---|---|---|
| 火山引擎方舟（主路线） | console.volcengine.com/ark → API Key管理；「开通管理」页开通模型后**复制确切模型ID** | 新用户通常有免费tokens与图片体验额度，以控制台「免费额度」页为准 |
| 智谱（备用） | open.bigmodel.cn | GLM-4-Flash（文本）、CogView-3-Flash（文生图）免费档 |
| Pollinations | 无需Key | 免费、限流，原型期使用 |
| mock | 无需Key | 本地离线，全流程演示 |

```bash
cp .env.example .env   # 填入 ARK_API_KEY 与模型ID
```

**安全约定**：`.env` 已被 .gitignore；Key只放后端；公网部署务必设置随机 `SECRET_KEY`。

## 重要说明

- **模型开通清单**（方舟控制台「开通管理」页）：`doubao-seed-2-0-lite`（文案）、`doubao-seedream-5-0`（插画/扮相）、`doubao-seedance-2-0-mini`（视频，暂未开通则视频功能会提示"模型未开通"）；
- **模型ID带日期后缀**，必须与控制台显示一致，404基本都是ID不对或未开通；
- **数据库升级说明**：v0.3 起用户表为手机号体系，旧演示账号已重置，首次运行请重新注册；
- **任务持久化**：任务与结果媒体落库落盘（`data/puju.db` + `data/task_media/`）；视频任务重启后自动续查，图像/文案任务若遇服务重启会标记失败需重新生成；
- **数据库**：开发期 SQLite（自动创建）；切 MySQL 只需 `.env` 设置 `DATABASE_URL=mysql+pymysql://user:pwd@host:3306/puju?charset=utf8mb4`；
- **AI生成标识**：所有作品带「AI生成」徽标，符合《人工智能生成合成内容标识办法》要求；
- **费用提醒**：视频按秒计费（10秒720p约一两元/条量级，以控制台为准），演示期建议多用5秒+720p。

## 测试

```bash
python tests/smoke_test.py    # 离线冒烟：提示词/RAG/Provider/任务流（9项）
python tests/test_api_full.py # 全链路：注册→生成→存作品→广场→点赞→文件→删除（mock，无需Key）
```

## 与开题报告的对应

| 开题报告 | 代码落点 |
|---|---|
| 模块1：素材库（知识库/提示词素材/评估基准） | `data/knowledge/puju_knowledge.json`（种子，待素材库替换） |
| 模块2：提示词模板库、双层提示词机制 | `app/prompts/opera_templates.py` + `GET /api/templates` |
| 模块2：RAG知识注入 | `app/rag/knowledge.py` |
| 模块2/3：多模型服务适配（云端API可切换） | `app/providers/` |
| 模块3：智能创作工具（自设细节） | 创作台三页签 + `/api/generate/*` |
| 模块3：戏曲科普知识库 | `KnowledgeView.vue` + `/api/knowledge` |
| 模块3：用户互动（注册登录/作品广场/点赞） | `auth.py` + `works.py` + 前端广场/我的作品 |
| 模块3：异步任务机制 | `tasks.py`（前端轮询） |
| 模块3：AI生成内容标识 | 作品「AI生成」徽标 + 方舟水印参数 |
| 模块4：系统测试 | `tests/`（功能链路）；对比实验见下 |

## 下一步（对照开题报告）

1. 填入火山引擎Key实测生成效果，小批量验证 SeedEdit 扮相转换质量；
2. 素材库（200~300张）替换种子知识，RAG升级 bge-small-zh-v1.5 语义向量（CPU可跑）；
3. 提示词模板组件迁移 MySQL 字典表（`/api/templates` 接口不变）；
4. 生成质量对比实验：同一批输入，成对存档「通用提示词 vs 领域模板提示词」结果（论文实验章）；
5. 性能测试与用户体验问卷（20~30人，李克特五级量表）。

## 目录结构

```
puju-aigc/
├── app/
│   ├── config.py               # 配置与密钥
│   ├── prompts/opera_templates.py
│   ├── rag/knowledge.py
│   ├── providers/              # ark / zhipu / pollinations / mock
│   └── api/                    # main / tasks / auth / works / knowledge / db
├── puju-web/                   # Vue3 + Element Plus 前端（dist已预构建）
├── data/knowledge/puju_knowledge.json
├── tests/                      # smoke_test.py / test_api_full.py
├── streamlit_app.py            # Streamlit 快速演示
└── requirements.txt / .env.example
```

## FAQ

- **404/模型不存在**：模型ID不对或未开通，去方舟「开通管理」页核对。
- **401**：API Key错误（`.env`）或登录过期（重新登录）。
- **扮相转换提示不支持**：图像编辑仅 ark 支持，`.env` 设 `IMAGE_PROVIDER=ark` 并配置Key。
- **想重置演示数据**：删除 `data/puju.db` 与 `data/works/` 内文件后重启。
- **打包体积**：`puju-web/node_modules`（120MB）无需备份，任何机器 `npm install` 即可重建；zip包已排除。
