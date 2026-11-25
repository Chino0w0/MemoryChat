import json
from pathlib import Path
import httpx

from agent.skills import SkillLoader
from db.repository import Repository
from llm.provider import MultiProviderClient
from memory.pipeline import MemoryPipeline
from ml.embedder import MemoryEmbedder
from ml.memory_gate import MemoryGateClassifier


def _mock_llm_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]})

        body = json.loads(request.content.decode("utf-8"))
        if body.get("stream"):
            sse = (
                'data: {"choices":[{"delta":{"content":"你好，"}}]}\n\n'
                'data: {"choices":[{"delta":{"content":"已结合记忆为你解答。"}}]}\n\n'
                "data: [DONE]\n\n"
            )
            return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})

        # Non-streaming JSON extraction / summary fallback test
        user_msg = body["messages"][-1]["content"]
        if "浓缩为 JSON" in user_msg:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"summary_text":"完成了后端表结构讨论","key_topics":["SQLite","FastAPI"]}'}}]},
            )
        return httpx.Response(500, json={"error": "trigger local fallback"})

    return httpx.MockTransport(handler)


def test_openai_compatible_client_and_skills_loader():
    client = MultiProviderClient(transport=_mock_llm_transport())
    conn = client.test_connection("https://api.example.com/v1", "sk-test")
    assert conn["ok"] is True
    assert "deepseek-chat" in conn["models"]

    prov = {"id": "ds", "base_url": "https://api.example.com/v1", "api_key": "sk-test"}
    chunks = list(client.stream_chat(prov, "deepseek-chat", [{"role": "user", "content": "hi"}]))
    assert "".join(chunks) == "你好，已结合记忆为你解答。"

    skills_dir = Path(__file__).resolve().parents[2] / "skills"
    loader = SkillLoader(skills_dir)
    skill_names = {s["name"] for s in loader.list_skills()}
    assert {"persona-onboarding", "context-summarizer", "study-planner"}.issubset(skill_names)
    assert loader.load_skill_body("study-planner") is not None


def test_memory_pipeline_incognito_add_update_and_summary(tmp_path: Path):
    repo = Repository(tmp_path / "pipe.db")
    repo.init_db()
    gate = MemoryGateClassifier()
    embedder = MemoryEmbedder(use_bge_if_cached=False)
    llm = MultiProviderClient(transport=_mock_llm_transport())
    pipeline = MemoryPipeline(repo=repo, gate=gate, embedder=embedder, llm=llm, summary_trigger_count=4)

    conv = repo.create_conversation(title="测试记忆流")
    prov = {"id": "ds", "base_url": "https://api.example.com/v1", "api_key": "sk-test"}

    assert pipeline.process_turn(conv["id"], None, "我是计算机专业学生", prov, "deepseek-chat", memory_enabled=False) is None
    assert pipeline.process_turn(conv["id"], None, "哈哈哈好的明白啦", prov, "deepseek-chat", memory_enabled=True) is None

    add_ev = pipeline.process_turn(conv["id"], None, "我平时喝咖啡习惯喝全糖拿铁", prov, "deepseek-chat", memory_enabled=True)
    assert add_ev is not None and add_ev["action"] == "ADD"
    old_id = add_ev["memory"]["id"]

    upd_ev = pipeline.process_turn(conv["id"], None, "我现在戒糖了，以后喝咖啡改喝无糖冰美式", prov, "deepseek-chat", memory_enabled=True)
    assert upd_ev is not None and upd_ev["action"] == "UPDATE"
    assert repo.get_memory(old_id)["status"] == "archived"

    sys_prompt, refs = pipeline.prepare_context(conv["id"], "帮我点一杯咖啡", memory_enabled=True, top_k=5, threshold=0.10)
    assert len(refs) >= 1
    assert "无糖冰美式" in sys_prompt

    for idx in range(4):
        repo.add_message(conv["id"], "user" if idx % 2 == 0 else "assistant", f"第 {idx + 1} 轮讨论")
    summary = pipeline.maybe_update_summary(conv["id"], prov, "deepseek-chat")
    assert summary is not None
    assert "后端表结构" in summary["summary_text"]
