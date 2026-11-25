from pathlib import Path
from app.db.repository import Repository
from app.ml.memory_gate import MemoryGateClassifier
from app.ml.embedder import MemoryEmbedder
from app.llm.provider import MultiProviderClient, PRESET_PROVIDERS
from app.memory.pipeline import MemoryPipeline
from app.extensions.interfaces import ExtensionRegistry


def test_preset_providers_and_demo_stream():
    preset_ids = {p["id"] for p in PRESET_PROVIDERS}
    assert {"demo", "deepseek", "gemini", "openai", "ollama"}.issubset(preset_ids)

    client = MultiProviderClient()
    demo_cfg = {"id": "demo", "base_url": "local://demo", "api_key": ""}
    chunks = list(
        client.stream_chat(
            provider=demo_cfg,
            model="memorychat-demo",
            messages=[
                {"role": "system", "content": "<user_profile>\n- 偏爱 FastAPI\n</user_profile>"},
                {"role": "user", "content": "你好，推荐个框架"},
            ],
        )
    )
    full_text = "".join(chunks)
    assert len(full_text) > 0
    assert "FastAPI" in full_text


def test_memory_pipeline_incognito_add_update_and_summary(tmp_path: Path):
    repo = Repository(tmp_path / "pipe.db")
    repo.init_db()
    gate = MemoryGateClassifier()
    embedder = MemoryEmbedder()
    llm = MultiProviderClient()
    pipeline = MemoryPipeline(repo=repo, gate=gate, embedder=embedder, llm=llm, summary_trigger_count=4)

    conv = repo.create_conversation(title="测试记忆流")
    demo_provider = repo.get_provider("demo")
    assert demo_provider is not None

    # 1. Incognito skips writing and reading
    incog_event = pipeline.process_turn(
        conversation_id=conv["id"],
        message_id=None,
        user_text="我是大四计算机专业学生",
        provider=demo_provider,
        model="memorychat-demo",
        memory_enabled=False,
    )
    assert incog_event is None
    assert repo.list_memories(active_only=True) == []

    # 2. Chitchat skipped by MemoryGate
    skip_event = pipeline.process_turn(
        conversation_id=conv["id"],
        message_id=None,
        user_text="哈哈哈好的明白啦",
        provider=demo_provider,
        model="memorychat-demo",
        memory_enabled=True,
    )
    assert skip_event is None

    # 3. Persona preference added
    add_event = pipeline.process_turn(
        conversation_id=conv["id"],
        message_id=None,
        user_text="我平时喝咖啡习惯喝全糖拿铁",
        provider=demo_provider,
        model="memorychat-demo",
        memory_enabled=True,
    )
    assert add_event is not None
    assert add_event["action"] == "ADD"
    old_mem_id = add_event["memory"]["id"]

    # 4. Preference update supersedes old coffee habit
    upd_event = pipeline.process_turn(
        conversation_id=conv["id"],
        message_id=None,
        user_text="我现在戒糖了，以后喝咖啡改喝无糖冰美式",
        provider=demo_provider,
        model="memorychat-demo",
        memory_enabled=True,
    )
    assert upd_event is not None
    assert upd_event["action"] in {"UPDATE", "ADD"}
    if upd_event["action"] == "UPDATE":
        old_record = repo.get_memory(old_mem_id)
        assert old_record["status"] == "archived"

    # 5. Prompt preparation recalls active memory unless incognito
    sys_prompt, refs = pipeline.prepare_context(
        conversation_id=conv["id"],
        query="帮我点一杯我平时爱喝的咖啡",
        memory_enabled=True,
        top_k=5,
        threshold=0.1,
    )
    assert len(refs) >= 1
    assert "咖啡" in sys_prompt or "美式" in sys_prompt

    _, incog_refs = pipeline.prepare_context(
        conversation_id=conv["id"],
        query="帮我点一杯咖啡",
        memory_enabled=False,
    )
    assert incog_refs == []

    # 6. Rolling summary triggers after 4 messages
    for idx in range(4):
        repo.add_message(conv["id"], "user" if idx % 2 == 0 else "assistant", f"架构讨论第 {idx + 1} 轮：确定使用 FastAPI")
    summary = pipeline.maybe_update_summary(conv["id"], demo_provider, "memorychat-demo")
    assert summary is not None
    assert len(summary["summary_text"]) > 0


def test_extension_registry_reserved_slots():
    reg = ExtensionRegistry()
    slots = reg.list_slots()
    slot_ids = [s["slot"] for s in slots]
    assert slot_ids == ["asr", "skill", "tool"]
    assert all(s["status"] == "reserved" for s in slots)
