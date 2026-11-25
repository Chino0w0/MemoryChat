from pathlib import Path
from db.repository import Repository


def test_clean_empty_providers_and_crud(tmp_path: Path):
    repo = Repository(tmp_path / "mc.db")
    repo.init_db()
    # Zero fake presets seeded on fresh init
    assert repo.list_providers() == []

    saved = repo.upsert_provider(
        provider_id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        api_key="sk-test-123",
        models=["deepseek-chat"],
    )
    assert saved["id"] == "deepseek"
    assert saved["has_key"] is True
    assert len(repo.list_providers()) == 1


def test_conversation_incognito_and_messages(tmp_path: Path):
    repo = Repository(tmp_path / "mc.db")
    repo.init_db()

    conv = repo.create_conversation(title="新对话", memory_enabled=True)
    assert conv["memory_enabled"] is True

    updated = repo.update_conversation(conv["id"], memory_enabled=False, title="无痕会话")
    assert updated["memory_enabled"] is False
    assert updated["title"] == "无痕会话"

    msg = repo.add_message(
        conversation_id=conv["id"],
        role="user",
        content="你好",
        memory_refs=[{"id": "m1", "score": 0.88}],
    )
    msgs = repo.list_messages(conv["id"])
    assert len(msgs) == 1
    assert msgs[0]["id"] == msg["id"]


def test_memory_crud_toggle_and_replacement_chain(tmp_path: Path):
    repo = Repository(tmp_path / "mc.db")
    repo.init_db()

    m1 = repo.add_memory(
        layer="profile",
        category="preference",
        content="喜欢喝全糖咖啡",
        confidence=0.91,
        embedding_blob=b"\x00" * 2048,
        is_pinned=True,
    )
    assert len(repo.list_injectable_memories()) == 1

    toggled = repo.update_memory(m1["id"], is_enabled=False)
    assert toggled["is_enabled"] is False
    assert len(repo.list_memories(active_only=True)) == 1
    assert len(repo.list_injectable_memories()) == 0

    repo.update_memory(m1["id"], is_enabled=True)
    m2 = repo.add_memory(
        layer="profile",
        category="preference",
        content="喜欢喝无糖冰美式",
        confidence=0.95,
        embedding_blob=b"\x00" * 2048,
    )
    archived = repo.archive_memory(m1["id"], replaced_by_id=m2["id"])
    assert archived["status"] == "archived"
    assert archived["replaced_by_id"] == m2["id"]
    assert [m["id"] for m in repo.list_memories(active_only=True)] == [m2["id"]]

    # Undo restores superseded m1
    repo.archive_memory(m2["id"], replaced_by_id=None)
    assert [m["id"] for m in repo.list_memories(active_only=True)] == [m1["id"]]


def test_session_summary_upsert(tmp_path: Path):
    repo = Repository(tmp_path / "mc.db")
    repo.init_db()
    conv = repo.create_conversation(title="长对话")

    s1 = repo.upsert_summary(
        conversation_id=conv["id"],
        summary_text="讨论了 FastAPI 架构设计",
        key_topics=["FastAPI"],
        covered_until_msg_id="msg_6",
        embedding_blob=b"\x00" * 2048,
    )
    s2 = repo.upsert_summary(
        conversation_id=conv["id"],
        summary_text="敲定了 SQLite 五张表",
        key_topics=["SQLite"],
        covered_until_msg_id="msg_12",
        embedding_blob=b"\x00" * 2048,
    )
    fetched = repo.get_summary(conv["id"])
    assert fetched is not None
    assert fetched["id"] == s1["id"]
    assert fetched["summary_text"] == s2["summary_text"]
