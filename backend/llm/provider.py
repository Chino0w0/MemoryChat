from __future__ import annotations

import json
import re
from typing import Any, Iterator

import httpx

UPDATE_CUES = ("改喝", "改成", "改为", "不再", "戒", "换成", "以后只", "现在改")


class MultiProviderClient:
    """Unified OpenAI-compatible streaming client supporting DeepSeek, Gemini, OpenAI, and Ollama."""

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def _client(self, timeout: float = 60.0) -> httpx.Client:
        return httpx.Client(timeout=timeout, transport=self._transport)

    @staticmethod
    def _headers(api_key: str = "") -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        return headers

    def test_connection(self, base_url: str, api_key: str = "") -> dict[str, Any]:
        url = f"{base_url.rstrip('/')}/models"
        with self._client(timeout=15.0) as client:
            resp = client.get(url, headers=self._headers(api_key))
            resp.raise_for_status()
            body = resp.json()
            data_list = body.get("data", []) if isinstance(body, dict) else []
            models = [str(item.get("id")) for item in data_list if isinstance(item, dict) and item.get("id")]
            return {"ok": True, "models": models}

    def stream_chat(
        self,
        provider: dict[str, Any],
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        base_url = (provider.get("base_url") or "").strip()
        if not base_url:
            raise ValueError("Provider base_url is required")

        url = f"{base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = tools

        with self._client(timeout=60.0) as client:
            with client.stream("POST", url, headers=self._headers(provider.get("api_key", "")), json=payload) as resp:
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

    def complete_json(
        self,
        provider: dict[str, Any],
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any] | None:
        base_url = (provider.get("base_url") or "").strip()
        if not base_url:
            return None
        url = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        with self._client(timeout=30.0) as client:
            resp = client.post(url, headers=self._headers(provider.get("api_key", "")), json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            return json.loads(match.group(0)) if match else None

    def extract_memory_decision(
        self,
        provider: dict[str, Any],
        model: str,
        user_text: str,
        gate_label: str,
        similar_memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        existing_desc = "\n".join(f"- id={m['id']}: {m['content']}" for m in similar_memories[:3]) or "无"
        prompt = (
            "从用户发言中提炼单条个人记忆，返回纯 JSON："
            '{"action":"ADD|UPDATE|NONE","layer":"profile|episodic","category":"identity|preference|habit|project","content":"...","target_id":null}\n'
            f"预判层级：{gate_label}\n已有相近记忆：\n{existing_desc}\n用户原话：{user_text}"
        )
        try:
            parsed = self.complete_json(provider, model, "只返回合法 JSON 对象，禁止代码块。", prompt)
            if parsed and parsed.get("action") in {"ADD", "UPDATE", "NONE"}:
                return parsed
        except Exception:
            pass
        return self._fallback_extract(user_text, gate_label, similar_memories)

    @staticmethod
    def _fallback_extract(
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
            if any(cue in cleaned for cue in UPDATE_CUES) or top.get("score", 0.0) >= 0.55:
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
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-8:])
        prompt = (
            '将以下对话浓缩为 JSON：{"summary_text":"200字以内阶段总结","key_topics":["关键词1","关键词2"]}\n'
            f"先前摘要：{prev_summary or '无'}\n近期对话：\n{history_text}"
        )
        try:
            parsed = self.complete_json(provider, model, "只返回合法 JSON 对象。", prompt)
            if parsed and parsed.get("summary_text"):
                return {
                    "summary_text": str(parsed["summary_text"])[:300],
                    "key_topics": [str(t) for t in (parsed.get("key_topics") or [])][:5],
                }
        except Exception:
            pass

        snippets = [f"{m['role']}: {m['content'][:45]}" for m in messages[-6:]]
        base = f"{prev_summary} | " if prev_summary else ""
        summary_text = f"{base}讨论摘要：{'；'.join(snippets)}"[:280]
        topics = list(dict.fromkeys(re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,4}", summary_text)))[:5]
        return {"summary_text": summary_text, "key_topics": topics}
