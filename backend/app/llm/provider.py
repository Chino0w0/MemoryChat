from __future__ import annotations

import json
import re
from typing import Any, Iterator

import httpx

PRESET_PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "demo",
        "name": "Local Demo",
        "badge": "⚡",
        "base_url": "local://demo",
        "models": ["memorychat-demo"],
        "requires_key": False,
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "badge": "🐋",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "requires_key": True,
    },
    {
        "id": "gemini",
        "name": "Gemini",
        "badge": "✦",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro"],
        "requires_key": True,
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "badge": "◎",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "requires_key": True,
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "badge": "🦙",
        "base_url": "http://127.0.0.1:11434/v1",
        "models": ["qwen2.5:7b", "llama3.2"],
        "requires_key": False,
    },
]

UPDATE_CUES = ("改喝", "改成", "改为", "不再", "戒", "换成", "以后只", "现在改")


class MultiProviderClient:
    """Unified OpenAI-compatible streaming client with built-in zero-key demo mode."""

    def stream_chat(
        self,
        provider: dict[str, Any],
        model: str,
        messages: list[dict[str, str]],
    ) -> Iterator[str]:
        base_url = (provider.get("base_url") or "").strip()
        if provider.get("id") == "demo" or base_url.startswith("local://"):
            yield from self._demo_stream(messages)
            return

        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        api_key = (provider.get("api_key") or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"model": model, "messages": messages, "stream": True}
        with httpx.Client(timeout=60.0) as client:
            with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except Exception:
                        continue

    @staticmethod
    def _demo_stream(messages: list[dict[str, str]]) -> Iterator[str]:
        sys_text = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

        mem_lines = [
            ln.strip("- ").strip()
            for ln in re.findall(r"^- .+$", sys_text, flags=re.MULTILINE)
        ]
        if mem_lines:
            reply = f"结合你的个人记忆（{'；'.join(mem_lines[:2])}），针对「{user_text[:28]}」为你提供贴合习惯的解答。"
        else:
            reply = f"已收到：「{user_text[:36]}」。你可以直接告诉我你的背景或偏好，我会自动为你沉淀个人记忆；也可点击顶部模型胶囊接入 DeepSeek / Gemini API。"

        step = 12
        for i in range(0, len(reply), step):
            yield reply[i : i + step]

    def extract_memory_decision(
        self,
        provider: dict[str, Any],
        model: str,
        user_text: str,
        gate_label: str,
        similar_memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        base_url = (provider.get("base_url") or "").strip()
        if provider.get("id") != "demo" and not base_url.startswith("local://"):
            try:
                return self._remote_extract(provider, model, user_text, gate_label, similar_memories)
            except Exception:
                pass
        return self._heuristic_extract(user_text, gate_label, similar_memories)

    def _remote_extract(
        self,
        provider: dict[str, Any],
        model: str,
        user_text: str,
        gate_label: str,
        similar_memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        existing_desc = "\n".join(f"- id={m['id']}: {m['content']}" for m in similar_memories[:3]) or "无"
        prompt = (
            "请从用户原话中提炼单条精炼的个人记忆，返回纯JSON对象："
            '{"action":"ADD|UPDATE|NONE","layer":"profile|episodic","category":"identity|preference|habit|project","content":"...","target_id":null}\n'
            f"预判层级：{gate_label}\n已有相近记忆：\n{existing_desc}\n用户原话：{user_text}"
        )
        chunks = list(
            self.stream_chat(
                provider,
                model,
                [{"role": "system", "content": "只输出合法JSON，不要代码块。"}, {"role": "user", "content": prompt}],
            )
        )
        raw = "".join(chunks).strip()
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            if parsed.get("action") in {"ADD", "UPDATE", "NONE"}:
                return parsed
        return self._heuristic_extract(user_text, gate_label, similar_memories)

    @staticmethod
    def _heuristic_extract(
        user_text: str,
        gate_label: str,
        similar_memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cleaned = re.sub(r"^(记住|请记住|顺便说一下)[，：:\s]*", "", user_text.strip()).rstrip("。！？!?")
        if "室友" in cleaned and "我" not in cleaned.replace("我室友", ""):
            return {"action": "NONE"}

        category = "project" if gate_label == "episodic" else "preference"
        if any(k in cleaned for k in ("学生", "工程师", "专业", "我叫", "在读")):
            category = "identity"
        elif any(k in cleaned for k in ("喝", "吃", "早起", "熬夜", "习惯")):
            category = "habit"

        if similar_memories:
            top = similar_memories[0]
            if top.get("content") == cleaned:
                return {"action": "NONE"}
            has_update_cue = any(cue in cleaned for cue in UPDATE_CUES)
            if has_update_cue or top.get("score", 0.0) >= 0.55:
                return {
                    "action": "UPDATE",
                    "layer": gate_label,
                    "category": category,
                    "content": cleaned,
                    "target_id": top["id"],
                }

        return {
            "action": "ADD",
            "layer": gate_label,
            "category": category,
            "content": cleaned,
            "target_id": None,
        }

    def summarize_messages(
        self,
        provider: dict[str, Any],
        model: str,
        prev_summary: str | None,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        snippets = [f"{m['role']}: {m['content'][:45]}" for m in messages[-6:]]
        joined = "；".join(snippets)
        base = f"{prev_summary} | " if prev_summary else ""
        summary_text = f"{base}近期讨论要点：{joined}"[:280]
        topics = list(dict.fromkeys(re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,4}", summary_text)))[:5]
        return {"summary_text": summary_text, "key_topics": topics}
