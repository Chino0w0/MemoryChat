from __future__ import annotations

from typing import Any

from db.repository import Repository
from llm.provider import MultiProviderClient
from ml.embedder import MemoryEmbedder
from ml.memory_gate import MemoryGateClassifier

BASE_SYSTEM_PROMPT = (
    "你是 MemoryChat 个人 AI 助手。请自然结合下方已知的用户画像与相关记忆来回答问题；"
    "若某条记忆与当前问题无关，请直接忽略。"
)


class MemoryPipeline:
    """Orchestrates pre-turn layered recall and post-turn MemoryGate filtering + summary compression."""

    def __init__(
        self,
        repo: Repository,
        gate: MemoryGateClassifier,
        embedder: MemoryEmbedder,
        llm: MultiProviderClient,
        summary_trigger_count: int = 10,
    ):
        self.repo = repo
        self.gate = gate
        self.embedder = embedder
        self.llm = llm
        self.summary_trigger_count = summary_trigger_count

    def prepare_context(
        self,
        conversation_id: str,
        query: str,
        memory_enabled: bool = True,
        top_k: int = 5,
        threshold: float = 0.20,
    ) -> tuple[str, list[dict[str, Any]]]:
        if not memory_enabled:
            return BASE_SYSTEM_PROMPT, []

        injectable = self.repo.list_injectable_memories(include_blob=True)
        pinned_profiles = [m for m in injectable if m["layer"] == "profile" or m["is_pinned"]]
        retrieved = self.embedder.retrieve(query=query, memories=injectable, top_k=top_k, threshold=threshold)

        seen_ids: set[str] = set()
        referenced: list[dict[str, Any]] = []
        for item in retrieved + pinned_profiles[:6]:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                clean_item = {k: v for k, v in item.items() if k != "embedding_blob"}
                clean_item.setdefault("score", 1.0 if clean_item.get("layer") == "profile" else 0.5)
                referenced.append(clean_item)

        sections = [BASE_SYSTEM_PROMPT]
        profile_lines = [f"- [{m['category']}] {m['content']}" for m in referenced if m["layer"] == "profile"]
        episodic_lines = [f"- [{m['category']}] {m['content']}" for m in referenced if m["layer"] == "episodic"]

        if profile_lines:
            sections.append("<user_profile>\n" + "\n".join(profile_lines) + "\n</user_profile>")
        if episodic_lines:
            sections.append("<relevant_memories>\n" + "\n".join(episodic_lines) + "\n</relevant_memories>")

        conv_summary = self.repo.get_summary(conversation_id)
        if conv_summary:
            sections.append(f"<session_summary>\n- {conv_summary['summary_text']}\n</session_summary>")

        return "\n\n".join(sections), referenced

    def process_turn(
        self,
        conversation_id: str,
        message_id: str | None,
        user_text: str,
        provider: dict[str, Any],
        model: str,
        memory_enabled: bool = True,
    ) -> dict[str, Any] | None:
        if not memory_enabled:
            return None

        gate_res = self.gate.predict(user_text)
        if gate_res.label == "skip":
            return None

        existing = self.repo.list_memories(active_only=True, include_blob=True)
        similar = self.embedder.retrieve(query=user_text, memories=existing, top_k=3, threshold=0.10)

        decision = self.llm.extract_memory_decision(
            provider=provider,
            model=model,
            user_text=user_text,
            gate_label=gate_res.label,
            similar_memories=similar,
        )
        action = decision.get("action", "NONE")
        if action not in {"ADD", "UPDATE"} or not decision.get("content"):
            return None

        layer = decision.get("layer") if decision.get("layer") in {"profile", "episodic"} else gate_res.label
        content = str(decision["content"]).strip()
        vec_blob = self.embedder.to_blob(self.embedder.encode(content))

        new_mem = self.repo.add_memory(
            layer=layer,
            category=str(decision.get("category") or "general"),
            content=content,
            source_message_id=message_id,
            source_quote=user_text[:120],
            confidence=gate_res.confidence,
            embedding_blob=vec_blob,
            is_pinned=(layer == "profile"),
        )

        target_id = decision.get("target_id")
        if action == "UPDATE" and target_id:
            self.repo.archive_memory(str(target_id), replaced_by_id=new_mem["id"])

        event = {"action": action, "gate_label": gate_res.label, "memory": new_mem}
        if message_id:
            self.repo.update_message_events(message_id, [event])
        return event

    def maybe_update_summary(
        self,
        conversation_id: str,
        provider: dict[str, Any],
        model: str,
    ) -> dict[str, Any] | None:
        messages = self.repo.list_messages(conversation_id)
        if len(messages) < self.summary_trigger_count:
            return None

        prev = self.repo.get_summary(conversation_id)
        if prev and prev.get("covered_until_msg_id") == messages[-1]["id"]:
            return prev

        res = self.llm.summarize_messages(
            provider=provider,
            model=model,
            prev_summary=prev["summary_text"] if prev else None,
            messages=messages,
        )
        blob = self.embedder.to_blob(self.embedder.encode(res["summary_text"]))
        return self.repo.upsert_summary(
            conversation_id=conversation_id,
            summary_text=res["summary_text"],
            key_topics=res["key_topics"],
            covered_until_msg_id=messages[-1]["id"],
            embedding_blob=blob,
        )
