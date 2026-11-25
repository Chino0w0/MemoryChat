from __future__ import annotations

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from agent.runner import AgentRunner  # noqa: E402
from agent.skills import SkillLoader  # noqa: E402
from agent.tools import ToolRegistry  # noqa: E402
from db.repository import Repository  # noqa: E402
from llm.provider import MultiProviderClient  # noqa: E402
from memory.pipeline import MemoryPipeline  # noqa: E402
from ml.embedder import MemoryEmbedder  # noqa: E402
from ml.memory_gate import MemoryGateClassifier  # noqa: E402
from routers.api import build_api_router  # noqa: E402


def create_app(
    db_path: str | Path | None = None,
    skills_dir: str | Path | None = None,
    llm_transport: httpx.BaseTransport | None = None,
) -> FastAPI:
    repo_root = BACKEND_ROOT.parent
    repo = Repository(db_path or (BACKEND_ROOT / "data" / "memorychat.db"))
    repo.init_db()

    gate_weights = BACKEND_ROOT / "data" / "memory_gate.joblib"
    gate = MemoryGateClassifier(model_path=gate_weights if gate_weights.exists() else None)
    embedder = MemoryEmbedder(use_bge_if_cached=False)
    llm = MultiProviderClient(transport=llm_transport)
    pipeline = MemoryPipeline(repo=repo, gate=gate, embedder=embedder, llm=llm)

    skills = SkillLoader(skills_dir or (repo_root / "skills"))
    tools = ToolRegistry()
    runner = AgentRunner(llm=llm, skills=skills, tools=tools)

    app = FastAPI(title="MemoryChat API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(
        build_api_router(
            repo=repo,
            embedder=embedder,
            llm=llm,
            pipeline=pipeline,
            runner=runner,
            skills=skills,
            tools=tools,
        )
    )
    return app


app = create_app()
