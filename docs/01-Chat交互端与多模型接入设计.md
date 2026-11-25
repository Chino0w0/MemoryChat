# 模块一 & 二：Chat 交互端与多模型接入设计

本文档定义 MemoryChat 的前端交互界面（模块一）与多供应商大模型自由接入层（模块二）。设计目标是打造**接近 Gemini / Cherry Studio 的清爽现代聊天体验**，将“个人记忆的感知与手动调控”自然融入聊天流，同时砍掉黑盒自动路由，把模型选择权完全交还给用户。

---

## 1. 功能清单与界面布局

### 1.1 三栏式清爽布局

```text
+--------------------+---------------------------------------------+------------------------+
| 左侧会话与导航栏    |               中央主对话工作区               |  右侧个人记忆控制台     |
| (Sidebar)          |               (ChatArea)                    |  (MemoryDrawer 可折叠)  |
|--------------------|---------------------------------------------|------------------------|
| [+ 新建对话]       | [模型下拉: DeepSeek-V3 v] [无痕模式: 关] [🧠] | [Tab: 画像 | 记忆 | 摘要]|
|                    |---------------------------------------------|------------------------|
| 今天               | 👤 用户：我平时写后端偏爱 FastAPI，不爱用     | 📌 核心画像 (常驻注入)  |
| - 课设架构讨论     |    Django，帮我起个接口模板。                | - 后端偏好 FastAPI [开] |
| 昨天               |   └─ ✨ 已记住：后端框架偏好 FastAPI [撤销]  | - CS 大四在读      [开] |
| - 周末健身计划     |                                             |                        |
|                    | 🤖 助手：[🔍 已参考 2 条个人记忆 ▾]          | 🧩 情景与偏好记忆       |
|--------------------|    按你习惯的 FastAPI + Pydantic v2 风格，   | - 课设12月20日截止 [开] |
| 🧩 Skill 技能库    |    为你生成如下精简路由模板...               | - 咖啡习惯美式无糖 [关] |
| ⚙️ 多模型接入设置  |---------------------------------------------|------------------------|
| 📊 小模型工作状态  | [/ 挂载Skill] [输入框...          ] [🎤][发送]| 🎚️ 召回条数 Top-5 / 阈值|
+--------------------+---------------------------------------------+------------------------+
```

### 1.2 核心交互特性（满足课设“用户可交互调整模块”要求）

1. **记忆透明化微交互（Gemini 风格）**
   - **引用折叠胶囊**：当本轮对话召回了个人记忆或历史会话摘要时，助手气泡顶部展示 `[🔍 已参考 N 条记忆]`，点击展开即可查看具体注入了哪几条记忆卡片及其相似度得分。
   - **写入实时提示**：当后台 `MemoryGate` 小模型捕获到有价值信息并完成提炼落库后，在对应用户消息下方温和浮现 `✨ 已更新记忆：... [编辑] [撤销]`，避免暗箱乱记。
2. **右侧「记忆与上下文控制台」（MemoryDrawer）**
   - 分三栏展示 **核心画像（Profile）**、**情景记忆（Episodic）**、**会话摘要（Summaries）**。
   - **细粒度人工干预**：支持手动新增一条画像、直接双击改写模型总结不准的记忆、点击开关临时屏蔽某条记忆（`is_enabled`）、点击图钉置顶常驻（`is_pinned`）。
   - **参数滑块调节**：用户可直观拖动滑块调整**单轮最大召回记忆条数（`Top-K`，1～10）**与**最低语义相似度阈值（如 `0.45`）**，实时控制上下文注入强度。
3. **单会话「无痕模式」开关**
   - 顶部一键开启无痕对话（`memory_enabled = false`）：本会话既不读取个人记忆，也不触发 `MemoryGate` 提取，适合临时帮别人问问题或测试纯裸模型效果（录屏演示“有记忆 vs 无记忆”对比时一键切换即可展示！）。
4. **轻量语音输入点缀（可选锦上添花，零后端负担）**
   - 输入框右侧保留一个轻量麦克风按钮 `[🎤]`，直接调用浏览器原生 `window.webkitSpeechRecognition`（Web Speech API）将语音实时转为输入框草稿文字，用户可改字后发送；无需额外部署重型流式语音服务器，仅约 30 行前端代码。

---

## 2. 多模型自由接入层设计（替代原黑盒路由）

聊天对话单轮上下文精简，与其用黑盒路由强行替用户做主，不如提供一套**通用的多供应商模型注册表**，让用户自由连接手头已有的任意 API 或本地模型。

### 2.1 支持的模型接入类型

统一采用 **OpenAI Chat Completions 兼容流式接口** 作为主通道（目前 95% 国内外厂商与本地框架均原生支持）：

| 供应商示例 | 默认 Base URL | 接入方式说明 |
| :--- | :--- | :--- |
| **DeepSeek** | `https://api.deepseek.com/v1` | 填入 API Key 即可选用 `deepseek-chat`、`deepseek-reasoner` |
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai/` | 直接走 Gemini 官方兼容端点（或可选 `google-genai` SDK），支持 `gemini-2.5-flash` / `pro` |
| **硅基流动 / 通义千问 / Moonshot** | 各平台官方 `/v1` 地址 | 一套统一协议无缝接入 Qwen、GLM、Kimi 等模型 |
| **Ollama / llama.cpp（纯本地）** | `http://127.0.0.1:11434/v1` | 免 API Key，直接连接本地部署的开源大模型 |

### 2.2 双角色模型配置（对话主模型 + 后台整理模型）

- **当前对话模型（Chat Model）**：聊天框顶部下拉框随时切换，支持在同一个会话里第 1 句用 `Gemini`、第 2 句切 `DeepSeek` 接着聊，所有模型共享同一个本地 SQLite 个人记忆库！
- **后台记忆整理模型（Memory Worker Model）**：在设置页可选择“跟随当前对话模型”（默认），或固定指定一个响应快、单价极低的轻量模型（例如 `deepseek-chat`、`gemini-2.5-flash` 或本地 `qwen2.5:3b`），专门负责 `MemoryGate` 放行后的 JSON 记忆提炼与长会话摘要生成。

### 2.3 模型供应商表结构与客户端实现契约

```sql
CREATE TABLE IF NOT EXISTS model_providers (
    id TEXT PRIMARY KEY,              -- 例如 'deepseek', 'gemini', 'ollama'
    name TEXT NOT NULL,               -- 显示名称，如 'DeepSeek 官方'
    base_url TEXT NOT NULL,           -- API 基础地址
    api_key TEXT DEFAULT '',          -- 本地存储的密钥（Ollama 可为空）
    models_json TEXT NOT NULL,        -- JSON 数组，如 '["deepseek-chat","deepseek-reasoner"]'
    is_enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);
```

Python 侧统一封装在 `backend/llm/provider.py`（核心逻辑约 100 行，极易讲解）：
- `stream_chat(provider_cfg, model, messages, tools=None)`：基于 `openai.AsyncOpenAI(base_url=..., api_key=...)` 发起 `stream=True` 请求；自动隔离并跳过推理模型的私有 `reasoning_content`（或单独放入前端可折叠思考框，绝不混入记忆库），统一向上游 `AgentRunner` 产出标准增量块与 `tool_calls`。
- `structured_completion(provider_cfg, model, system_prompt, user_prompt)`：用于后台记忆提炼与会话摘要，开启 JSON 输出约束并做容错解析。

---

## 3. 前后端 SSE 流式通信协议

前端发送消息统一调用 `POST /api/chat/stream`，后端以 `text/event-stream` 按序推送以下轻量 JSON 事件，一趟连接完成正文、工具状态、记忆引用与记忆更新通知：

| SSE `event` 类型 | 数据载荷示例 (`data`) | 前端界面响应行为 |
| :--- | :--- | :--- |
| `memory_context` | `{"items": [{"id": "m_12", "content": "后端偏好 FastAPI", "score": 0.84}]}` | 在助手回复气泡顶部渲染 `[🔍 已参考 1 条个人记忆]` |
| `skill_activated` | `{"name": "study-planner", "title": "学习规划助手"}` | 显示当前已挂载的技能标签 |
| `tool_call` | `{"call_id": "c1", "name": "memory_save", "status": "running"}` | 在消息流内显示轻量折叠工具执行条 |
| `text_delta` | `{"delta": "按你习惯的 FastAPI 风格..."}` | 实时追加渲染助手 Markdown 文本 |
| `done` | `{"message_id": "msg_89", "model": "deepseek-chat"}` | 结束打字机光标，固定消息状态 |
| `memory_updated` | `{"action": "ADD", "memory": {"id": "m_19", "content": "不喜欢用 Django"}}` | 异步任务完成后推送，点亮用户气泡下方 `✨ 已更新记忆` 并刷新右侧面板 |
