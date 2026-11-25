import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app


def _parse_sse(raw_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    current_event = "message"
    for line in raw_text.splitlines():
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            payload = json.loads(line.split(":", 1)[1].strip())
            events.append((current_event, payload))
    return events


def test_health_presets_and_extension_slots(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "api.db"))

    assert client.get("/api/health").status_code == 200
    presets = client.get("/api/providers/presets").json()
    assert any(p["id"] == "deepseek" for p in presets)

    slots = client.get("/api/extensions/slots").json()
    assert [s["slot"] for s in slots] == ["asr", "skill", "tool"]


def test_empty_message_rejected_with_422(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "api.db"))
    conv = client.post("/api/conversations", json={"title": "测试"}).json()
    resp = client.post(
        "/api/chat/stream",
        json={"conversation_id": conv["id"], "content": "   "},
    )
    assert resp.status_code == 422


def test_end_to_end_chat_memory_capture_recall_toggle_and_undo(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "api.db"))
    conv = client.post("/api/conversations", json={"title": "个人偏好"}).json()

    # Turn 1: User states persona preference -> MemoryGate + Pipeline captures it
    r1 = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conv["id"],
            "content": "我是大四计算机专业学生，平时写Python后端最喜欢用FastAPI",
        },
    )
    assert r1.status_code == 200
    ev1 = _parse_sse(r1.text)
    ev_names1 = [name for name, _ in ev1]
    assert "text_delta" in ev_names1
    assert "memory_updated" in ev_names1
    assert "done" in ev_names1

    mem_event = next(data for name, data in ev1 if name == "memory_updated")
    mem_id = mem_event["memory"]["id"]

    # Turn 2 in a brand-new conversation recalls the stored memory
    conv2 = client.post("/api/conversations", json={"title": "新窗口测试跨会话记忆"}).json()
    r2 = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conv2["id"],
            "content": "结合我的Python后端框架偏好给我一句建议",
        },
    )
    ev2 = _parse_sse(r2.text)
    ctx_event = next(data for name, data in ev2 if name == "memory_context")
    assert any(item["id"] == mem_id for item in ctx_event["items"])

    # Disable memory via drawer PATCH -> no longer recalled
    patch_resp = client.patch(f"/api/memories/{mem_id}", json={"is_enabled": False})
    assert patch_resp.status_code == 200
    r3 = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conv2["id"],
            "content": "再结合我的Python后端框架偏好说说",
        },
    )
    ctx_after_disable = next(data for name, data in _parse_sse(r3.text) if name == "memory_context")
    assert all(item["id"] != mem_id for item in ctx_after_disable["items"])

    # Undo endpoint archives memory cleanly
    undo_resp = client.post(f"/api/memories/{mem_id}/undo")
    assert undo_resp.status_code == 200
    assert client.get("/api/memories").json() == []
