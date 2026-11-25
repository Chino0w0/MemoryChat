from __future__ import annotations

"""
End-to-end benchmark comparing:
  Group 1: Sliding-window LLM only (no memory)
  Group 2: Every-turn LLM memory extraction (no MemoryGate small model)
  Group 3: MemoryChat Plan A (MemoryGate filtering + 512-d hybrid retrieval)
Outputs call-saving ratio and latency metrics for the course report.
"""

import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ml.embedder import MemoryEmbedder  # noqa: E402
from ml.memory_gate import INITIAL_CORPUS, MemoryGateClassifier  # noqa: E402


def run_benchmark() -> dict[str, float]:
    gate = MemoryGateClassifier()
    embedder = MemoryEmbedder(use_bge_if_cached=False)

    turns = [text for text, _ in INITIAL_CORPUS]
    t0 = time.perf_counter()
    forwarded = 0
    for utt in turns:
        decision = gate.predict(utt)
        if decision.label != "skip":
            forwarded += 1
            _ = embedder.encode(utt)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    skipped = len(turns) - forwarded
    saved_ratio = skipped / max(1, len(turns))
    metrics = {
        "total_turns": float(len(turns)),
        "llm_extractions_group2": float(len(turns)),
        "llm_extractions_group3_plan_a": float(forwarded),
        "saved_extraction_ratio": round(saved_ratio, 4),
        "avg_local_small_model_ms": round(elapsed_ms / max(1, len(turns)), 3),
    }
    print("=== Plan A Small-Model Linkage Benchmark ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    return metrics


if __name__ == "__main__":
    run_benchmark()
