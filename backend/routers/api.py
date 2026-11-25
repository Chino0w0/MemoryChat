from __future__ import annotations

import json
from typing import Any, Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from agent.runner import AgentRunner
from agent.skills import SkillLoader
from agent.tools import ToolRegistry
from db.repository import Repository
from llm.provider import MultiProviderClient
from memory.pipeline import MemoryPipeline
from ml.embedder import MemoryEmbedder


class ProviderUpsertRequest(BaseModel):
    id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=4, max_length=300)
    api_key: str = ""
    models: list[str] = Field(min_length=1)
    is_enabled: bool = True


class ProviderTestRequest(BaseModel):
    base_url: str = Field(min_length=4, max_length=300)
    api_key: str = ""


class ConversationCreateRequest(BaseModel):
    title: str = "新对话"
    active_provider_id: str = ""
    active_model: str = ""
    memory_enabled: bool = True
    active_skills: list[str] = Field(default_factory=list)


class ConversationPatchRequest(BaseModel):
    title: str | None = None
    active_provider_id: str | None = None
    active_model: str | None = None
    memory_enabled: bool | None = None
    active_skills: list[str] | None = None


class MemoryCreateRequest(BaseModel):
    layer: str = "profile"
    category: str = "preference"
    content: str = Field(min_length=1, max_length=300)
    is_pinned: bool = False

    @field_validator("content")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Memory content cannot be blank")
        return v.strip()


class MemoryPatchRequest(BaseModel):
    layer: str | None = None
    category: str | None = None
    content: str | None = None
    is_pinned: bool | None = None
    is_enabled: bool | None = None


class ChatStreamRequest(BaseModel):
    conversation_id: str
    content: str
    provider_id: str | None = None
    model: str | None = None
    memory_enabled: bool | None = None
    active_skills: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    threshold: float = Field(default=0.20, ge=0.0, le=0.95)

    @field_validator("content")
    @classmethod
    def _validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()


def _sse_frame(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_api_router(
    repo: Repository,
    embedder: MemoryEmbedder,
    llm: MultiProviderClient,
    pipeline: MemoryPipeline,
    runner: AgentRunner,
    skills: SkillLoader,
    tools: ToolRegistry,
) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": "1.0.0"}

    # ---- Providers ----
    @router.get("/providers")
    def list_providers() -> list[dict[str, Any]]:
        return repo.list_providers()

    @router.post("/providers")
    def upsert_provider(req: ProviderUpsertRequest) -> dict[str, Any]:
        cleaned_models = [m.strip() for m in req.models if m.strip()]
        if not cleaned_models:
            raise HTTPException(status_code=422, detail="At least one model ID is required")
        return repo.upsert_provider(
            provider_id=req.id.strip(),
            name=req.name.strip(),
            base_url=req.base_url.strip(),
            models=cleaned_models,
            api_key=req.api_key.strip(),
            is_enabled=req.is_enabled,
        )

    @router.post("/providers/test")
    def test_provider(req: ProviderTestRequest) -> dict[str, Any]:
        try:
            return llm.test_connection(base_url=req.base_url.strip(), api_key=req.api_key.strip())
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.delete("/providers/{provider_id}")
    def delete_provider(provider_id: str) -> dict[str, bool]:
        return {"deleted": repo.delete_provider(provider_id)}

    # ---- Conversations ----
    @router.get("/conversations")
    def list_conversations() -> list[dict[str, Any]]:
        return repo.list_conversations()

    @router.post("/conversations")
    def create_conversation(req: ConversationCreateRequest) -> dict[str, Any]:
        return repo.create_conversation(
            title=req.title,
            active_provider_id=req.active_provider_id,
            active_model=req.active_model,
            memory_enabled=req.memory_enabled,
            active_skills=req.active_skills,
        )

    @router.patch("/conversations/{conv_id}")
    def patch_conversation(conv_id: str, req: ConversationPatchRequest) -> dict[str, Any]:
        updated = repo.update_conversation(conv_id, **req.model_dump(exclude_none=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return updated

    @router.delete("/conversations/{conv_id}")
    def remove_conversation(conv_id: str) -> dict[str, bool]:
        return {"deleted": repo.delete_conversation(conv_id)}

    @router.get("/conversations/{conv_id}/messages")
    def list_messages(conv_id: str) -> list[dict[str, Any]]:
        return repo.list_messages(conv_id)

    # ---- Memories & Summaries ----
    @router.get("/memories")
    def list_memories(layer: str | None = None) -> list[dict[str, Any]]:
        return repo.list_memories(layer=layer, active_only=True)

    @router.post("/memories")
    def create_memory(req: MemoryCreateRequest) -> dict[str, Any]:
        layer = req.layer if req.layer in {"profile", "episodic"} else "profile"
        blob = embedder.to_blob(embedder.encode(req.content))
        return repo.add_memory(
            layer=layer,
            category=req.category,
            content=req.content,
            confidence=1.0,
            embedding_blob=blob,
            is_pinned=req.is_pinned or (layer == "profile"),
        )

    @router.patch("/memories/{mem_id}")
    def patch_memory(mem_id: str, req: MemoryPatchRequest) -> dict[str, Any]:
        fields = req.model_dump(exclude_none=True)
        if "content" in fields:
            fields["content"] = fields["content"].strip()
            fields["embedding_blob"] = embedder.to_blob(embedder.encode(fields["content"]))
        updated = repo.update_memory(mem_id, **fields)
        if not updated:
            raise HTTPException(status_code=404, detail="Memory not found")
        return updated

    @router.delete("/memories/{mem_id}")
    def delete_memory(mem_id: str) -> dict[str, Any]:
        archived = repo.archive_memory(mem_id)
        if not archived:
            raise HTTPException(status_code=404, detail="Memory not found")
        return archived

    @router.post("/memories/{mem_id}/undo")
    def undo_memory(mem_id: str) -> dict[str, Any]:
        archived = repo.archive_memory(mem_id, replaced_by_id=None)
        if not archived:
            raise HTTPException(status_code=404, detail="Memory not found")
        return archived

    @router.get("/summaries")
    def list_summaries() -> list[dict[str, Any]]:
        return repo.list_summaries()

    # ---- Skills & Extension Info ----
    @router.get("/skills")
    def list_skills() -> list[dict[str, str]]:
        return skills.list_skills()

    @router.get("/tools")
    def list_tools() -> list[dict[str, Any]]:
        return tools.list_schemas()

    # ---- Streaming Chat ----
    @router.post("/chat/stream")
    def chat_stream(req: ChatStreamRequest) -> StreamingResponse:
        conv = repo.get_conversation(req.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        provider_id = req.provider_id or conv["active_provider_id"]
        if not provider_id:
            providers = repo.list_providers()
            if not providers:
                raise HTTPException(status_code=400, detail="尚未配置任何模型服务商，请先在模型服务设置中添加接口。")
            provider_id = providers[0]["id"]

        provider = repo.get_provider(provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")

        model = req.model or conv["active_model"] or (provider["models"][0] if provider["models"] else "")
        if not model:
            raise HTTPException(status_code=400, detail="未指定可用模型 ID")

        mem_enabled = req.memory_enabled if req.memory_enabled is not None else conv["memory_enabled"]
        active_skills = req.active_skills if req.active_skills is not None else conv["active_skills"]

        history_rows = repo.list_messages(conv["id"])
        if not history_rows and conv["title"] == "新对话":
            repo.update_conversation(conv["id"], title=req.content[:20], active_provider_id=provider_id, active_model=model)

        sys_prompt, refs = pipeline.prepare_context(
            conversation_id=conv["id"],
            query=req.content,
            memory_enabled=mem_enabled,
            top_k=req.top_k,
            threshold=req.threshold,
        )

        user_msg = repo.add_message(conversation_id=conv["id"], role="user", content=req.content)
        clean_history = [
            {"role": m["role"], "content": m["content"]}
            for m in history_rows[-10:]
            if m["role"] in {"user", "assistant"}
        ]

        def event_stream() -> Iterator[str]:
            yield _sse_frame("memory_context", {"items": refs})
            collected: list[str] = []
            try:
                for delta in runner.stream_turn(
                    provider=provider,
                    model=model,
                    system_prompt=sys_prompt,
                    history=clean_history,
                    user_content=req.content,
                    active_skills=active_skills,
                ):
                    collected.append(delta)
                    yield _sse_frame("text_delta", {"delta": delta})
            except Exception as exc:
                err_msg = f"调用模型接口失败：{exc}"
                collected.append(err_msg)
                yield _sse_frame("text_delta", {"delta": err_msg})

            assistant_msg = repo.add_message(
                conversation_id=conv["id"],
                role="assistant",
                content="".join(collected),
                model_used=model,
                memory_refs=refs,
            )

            mem_event = pipeline.process_turn(
                conversation_id=conv["id"],
                message_id=user_msg["id"],
                user_text=req.content,
                provider=provider,
                model=model,
                memory_enabled=mem_enabled,
            )
            if mem_event:
                yield _sse_frame("memory_updated", mem_event)

            pipeline.maybe_update_summary(conv["id"], provider=provider, model=model)
            yield _sse_frame("done", {"message_id": assistant_msg["id"], "model": model})

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return router
