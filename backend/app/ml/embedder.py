from __future__ import annotations

import hashlib
import re
from typing import Any

import numpy as np

EMBED_DIM = 512
BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
STOP_CHARS = set("的了是在我有和就都而及与着或一个把被让给向从到对按请帮再说说看看呢吗吧啊呀哦哈")


def _extract_tokens(text: str) -> set[str]:
    norm = text.lower().strip()
    ascii_words = set(re.findall(r"[a-z0-9_+#.-]{2,}", norm))
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", norm)
    cjk_grams: set[str] = set()
    for run in cjk_runs:
        filtered = "".join(ch for ch in run if ch not in STOP_CHARS)
        for i in range(len(filtered) - 1):
            cjk_grams.add(filtered[i : i + 2])
        if len(filtered) == 1:
            cjk_grams.add(filtered)
    return ascii_words | cjk_grams


class MemoryEmbedder:
    """Plan A Small Model #2: 512-d semantic embedder (bge-small-zh-v1.5 with deterministic local fallback)."""

    def __init__(self, use_bge_if_cached: bool = False):
        self._bge_model = None
        if use_bge_if_cached:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._bge_model = SentenceTransformer("BAAI/bge-small-zh-v1.5", local_files_only=True)
            except Exception:
                self._bge_model = None

    def encode(self, text: str, is_query: bool = False) -> np.ndarray:
        cleaned = (text or "").strip()
        if not cleaned:
            vec = np.zeros(EMBED_DIM, dtype=np.float32)
            vec[0] = 1.0
            return vec

        if self._bge_model is not None:
            payload = f"{BGE_QUERY_PREFIX}{cleaned}" if is_query else cleaned
            arr = np.asarray(self._bge_model.encode(payload, normalize_embeddings=True), dtype=np.float32)
            return arr

        # Fast deterministic 512-d signed feature hashing over char 1-3 grams + ASCII tokens
        norm = cleaned.lower()
        features: list[tuple[str, float]] = []
        for token in re.findall(r"[a-z0-9_+#.-]{2,}", norm):
            features.append((f"w:{token}", 2.5))
        compact = re.sub(r"\s+", "", norm)
        for n, weight in ((1, 0.4), (2, 1.4), (3, 1.8)):
            for i in range(max(0, len(compact) - n + 1)):
                gram = compact[i : i + n]
                if n == 1 and gram in STOP_CHARS:
                    continue
                features.append((gram, weight))

        vec = np.zeros(EMBED_DIM, dtype=np.float32)
        for feat, weight in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            val = int.from_bytes(digest, "little")
            idx = val % EMBED_DIM
            sign = 1.0 if ((val >> 9) & 1) == 0 else -1.0
            vec[idx] += sign * weight

        norm_val = float(np.linalg.norm(vec))
        if norm_val < 1e-8:
            vec[0] = 1.0
            return vec
        return (vec / norm_val).astype(np.float32)

    @staticmethod
    def to_blob(vec: np.ndarray) -> bytes:
        arr = np.asarray(vec, dtype="<f4")
        if arr.shape != (EMBED_DIM,):
            raise ValueError(f"Expected ({EMBED_DIM},) float32 vector, got {arr.shape}")
        return arr.tobytes()

    @staticmethod
    def from_blob(blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype="<f4").copy()

    def retrieve(
        self,
        query: str,
        memories: list[dict[str, Any]],
        top_k: int = 5,
        threshold: float = 0.15,
    ) -> list[dict[str, Any]]:
        eligible = [
            m
            for m in memories
            if m.get("status", "active") == "active" and bool(m.get("is_enabled", True))
        ]
        if not eligible or not query.strip():
            return []

        q_vec = self.encode(query, is_query=True)
        q_tokens = _extract_tokens(query)

        scored: list[dict[str, Any]] = []
        for item in eligible:
            blob = item.get("embedding_blob")
            m_vec = self.from_blob(blob) if blob and len(blob) == EMBED_DIM * 4 else self.encode(item["content"])
            vec_score = max(0.0, float(np.dot(m_vec, q_vec)))

            m_tokens = _extract_tokens(item["content"])
            overlap = len(q_tokens & m_tokens) / max(1, min(len(q_tokens), 4)) if q_tokens else 0.0
            kw_score = min(1.0, overlap)

            final_score = 0.85 * vec_score + 0.15 * kw_score
            if final_score >= threshold:
                enriched = {k: v for k, v in item.items() if k != "embedding_blob"}
                enriched["score"] = round(final_score, 4)
                scored.append(enriched)

        scored.sort(key=lambda x: (x["score"], x.get("is_pinned", False)), reverse=True)
        return scored[:top_k]
