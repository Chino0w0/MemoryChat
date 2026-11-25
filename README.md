# MemoryChat

一个以**分层个人记忆与跨会话上下文理解**为核心的多模型 AI Chat 客户端（结合方案 A 双小模型联动与 `SKILL.md` 渐进式插件扩展）。

## 工程目录结构

```text
MemoryChat/
├── backend/                        # Python FastAPI 后端
│   ├── main.py                     # 应用入口、CORS、组件装配
│   ├── db/                         # schema.sql (5张核心表) + repository.py
│   ├── llm/                        # provider.py (统一 OpenAI 兼容多服务商客户端)
│   ├── ml/                         # memory_gate.py (自训三分类) + embedder.py (512维混合检索)
│   ├── memory/                     # pipeline.py (记忆提炼合并与会话滚动摘要)
│   ├── agent/                      # runner.py + tools.py + skills.py (Pi/DSH 风格扩展层)
│   ├── routers/                    # api.py (REST + SSE 流式路由)
│   └── tests/                      # 单元与端到端集成测试套件
├── frontend/                       # React 18 + TypeScript + Tailwind + Zustand 前端
│   ├── ui-prototype.html           # 独立自包含的主流 Chat 端交互 HTML 设计稿（可直接浏览器打开）
│   └── src/
│       ├── store/useChatStore.ts   # 全局会话、模型、记忆抽屉与 SSE 流状态
│       └── components/             # Sidebar / ChatArea / MemoryDrawer / ModelSettings
├── skills/                         # 兼容 Pi / DSH 规范的本地 SKILL.md 技能目录
│   ├── persona-onboarding/SKILL.md
│   ├── context-summarizer/SKILL.md
│   └── study-planner/SKILL.md
└── ml_experiments/                 # 课设小模型训练与对比评测目录
    ├── download_dulemon.py
    ├── train_memory_gate.py
    └── eval_pipeline.py
```

## 快速启动

### 1. 启动后端
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 2. 启动前端
```powershell
cd frontend
npm install
npm run dev
```

> 也可直接在浏览器中打开 [frontend/ui-prototype.html](frontend/ui-prototype.html) 预览完整的主流 Chat 端交互版式。

## 设计文档导航

- **快速概览**：[方案规划.md](docs/方案规划.md)
- **项目总纲与排期**：[MemoryChat产品设计与分期开发方案.md](docs/MemoryChat产品设计与分期开发方案.md)
- **模块一 & 二（前端与多模型层）**：[01-Chat交互端与多模型接入设计.md](docs/01-Chat交互端与多模型接入设计.md)
- **模块三（分层记忆存储与检索层）**：[02-分层个人记忆与存储检索设计.md](docs/02-分层个人记忆与存储检索设计.md)
- **模块四（小模型训练与对比评测层）**：[03-记忆小模型联动与评测设计.md](docs/03-记忆小模型联动与评测设计.md)
- **模块五（Agent 工具与 Skill 插件层）**：[04-Agent循环与Skill插件设计.md](docs/04-Agent循环与Skill插件设计.md)
- **模块六（主流 Chat 端 UI/UX 设计规范）**：[05-UIUX视觉与图形引导设计.md](docs/05-UIUX视觉与图形引导设计.md)
