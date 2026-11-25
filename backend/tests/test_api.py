import json
from pathlib import Path
import httpx
from fastapi.testclient import TestClient

from main import create_app


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "deepseek-chat"}]})
        body = json.loads(request.content.decode("utf-8"))
        if body.get("stream"):
            sse = (
                'data: {"choices":[{"delta":{"content":"收到，按 FastAPI 风格回复。"}}]}\n\n'
                "data: [DONE]\n\n"
            )
            return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
        return httpx.Response(500, json={"error": "use fallback extractor"})

    return httpx.MockTransport(handler)


def _parse_sse(raw_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    current_event = "message"
    for line in raw_text.splitlines():
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            events.append((current_event, json.loads(line.split(":", 1)[1].strip())))
    return events


def test_health_skills_and_unconfigured_provider_guard(tmp_path: Path):
    client = TestClient(create_app(db_path=tmp_path / "api.db", llm_transport=_mock_transport()))
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/providers").json() == []
    assert len(client.get("/api/skills").json()) >= 3

    conv = client.post("/api/conversations", json={"title": "未配模型测试"}).json()
    # Sending before configuring any provider returns clean 400
    no_prov = client.post("/api/chat/stream", json={"conversation_id": conv["id"], "content": "你好"})
    assert no_prov.status_code == 400


def test_empty_message_rejected_with_422(tmp_path: Path):
    client = TestClient(create_app(db_path=tmp_path / "api.db", llm_transport=_mock_transport()))
    conv = client.post("/api/conversations", json={"title": "空消息测试"}).json()
    resp = client.post("/api/chat/stream", json={"conversation_id": conv["id"], "content": "   "})
    assert resp.status_code == 422


def test_end_to_end_provider_setup_chat_recall_toggle_and_undo(tmp_path: Path):
    client = TestClient(create_app(db_path=tmp_path / "api.db", llm_transport=_mock_transport()))

    # 1. Test connection & save custom provider
    conn = client.post("/api/providers/test", json={"base_url": "https://api.deepseek.com/v1", "api_key": "sk-1"}).json()
    assert conn["ok"] is True

    client.post(
        "/api/providers",
        json={
            "id": "deepseek",
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "sk-1",
            "models": conn["models"],
        },
    )

    conv1 = client.post("/api/conversations", json={"title": "会话1"}).json()
    r1 = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conv1["id"],
            "provider_id": "deepseek",
            "model": "deepseek-chat",
            "content": "我是计算机专业学生，平时写Python后端最喜欢用FastAPI",
        },
    )
    assert r1.status_code == 200
    ev1 = _parse_sse(r1.text)
    mem_event = next(data for name, data in ev1 if name == "memory_updated")
    mem_id = mem_event["memory"]["id"]

    # 2. Cross-conversation recall
    conv2 = client.post("/api/conversations", json={"title": "会话2"}).json()
    r2 = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conv2["id"],
            "provider_id": "deepseek",
            "model": "deepseek-chat",
            "content": "结合我的Python后端框架偏好给个建议",
        },
    )
    ctx_event = next(data for name, data in _parse_sse(r2.text) if name == "memory_context")
    assert any(item["id"] == mem_id for item in ctx_event["items"])

    # 3. Disable in drawer -> excluded from recall
    client.patch(f"/api/memories/{mem_id}", json={"is_enabled": False})
    r3 = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conv2["id"],
            "provider_id": "deepseek",
            "model": "deepseek-chat",
            "content": "再结合我的Python后端框架偏好说说",
        },
    )
    ctx_disabled = next(data for name, data in _parse_sse(r3.text) if name == "memory_context")
    assert all(item["id"] != mem_id for item in ctx_disabled["items"])

    # 4. Undo archives cleanly
    assert client.post(f"/api/memories/{mem_id}/undo").status_code == 200
    assert client.get("/api/memories").json() == []
