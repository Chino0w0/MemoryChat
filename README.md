# MemoryChat

一个真正“懂你”的个人记忆型多模型 AI Chat 客户端——采用**极简图形化交互引导**与**“大模型 + 双小模型”协同记忆架构**。

## 分期演进路线

- **一期基础框架（当前实现 v1.0 Foundation）**：
  1. **少文字图形引导式 Chat UI**：图标胶囊顶栏、3 张图形破冰引导卡、气泡级微徽章反馈（`[🧠 ×N]` 溯源 / `[✨ +记忆 ↩]` 单步撤销）、右侧可视化记忆调控抽屉。
  2. **多模型自由接入与一键品牌预设**：原生模态卡片一键点选接入 DeepSeek、Gemini、OpenAI 兼容接口或本地 Ollama，内置免 Key 演示引擎开箱即用。
  3. **三层个人记忆与上下文总结**：SQLite 单文件管理「核心用户画像（`profile`）+ 情景与偏好记忆（`episodic`）+ 会话滚动摘要（`session_summary`）」。
  4. **方案 A 双小模型联动**：自训中文记忆价值三分类小模型（`MemoryGate`）毫秒级过滤闲聊废话 + 混合语义向量检索器（`MemoryEmbedder`，支持 `bge-small-zh-v1.5` 与轻量本地特征平滑降级）。
  5. **二期标准化扩展槽位（Extension Slots）**：前后端预留统一的 `Voice (ASR/TTS)`、`Skill (SKILL.md)` 与 `Tool (Function Calling)` 扩展接口，后续按插槽无缝扩充。

## 快速启动

### 1. 启动 Python 后端
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### 2. 启动 React 前端
```powershell
cd frontend
npm install
npm run dev
```

## 设计文档导航

- **快速概览**：[方案规划.md](docs/方案规划.md)
- **项目总纲与课设排期**：[MemoryChat产品设计与分期开发方案.md](docs/MemoryChat产品设计与分期开发方案.md)
- **模块一 & 二（前端与多模型层）**：[01-Chat交互端与多模型接入设计.md](docs/01-Chat交互端与多模型接入设计.md)
- **模块三（分层记忆存储与检索层）**：[02-分层个人记忆与存储检索设计.md](docs/02-分层个人记忆与存储检索设计.md)
- **模块四（小模型训练与对比评测层）**：[03-记忆小模型联动与评测设计.md](docs/03-记忆小模型联动与评测设计.md)
- **模块五（二期扩展：Agent 工具与 Skill 插件层）**：[04-Agent循环与Skill插件设计.md](docs/04-Agent循环与Skill插件设计.md)
- **模块六（UI/UX 图形引导视觉规范）**：[05-UIUX视觉与图形引导设计.md](docs/05-UIUX视觉与图形引导设计.md)
- **一期基础框架实施计划**：[2026-11-25-memorychat-foundation.md](docs/superpowers/plans/2026-11-25-memorychat-foundation.md)
