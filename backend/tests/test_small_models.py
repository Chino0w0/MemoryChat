import numpy as np
from pathlib import Path
from ml.memory_gate import MemoryGateClassifier
from ml.embedder import MemoryEmbedder


def test_memory_gate_three_class_predictions(tmp_path: Path):
    gate = MemoryGateClassifier()

    assert gate.predict("哈哈哈好的谢谢，帮我写一段快速排序代码").label == "skip"

    profile_res = gate.predict("我是计算机专业学生，平时写Python后端偏爱用FastAPI")
    assert profile_res.label == "profile"
    assert profile_res.confidence >= 0.45

    episodic_res = gate.predict("下周五之前我要提交综合实习报告，这几天都在赶进度")
    assert episodic_res.label == "episodic"
    assert episodic_res.confidence >= 0.45

    model_file = tmp_path / "gate.joblib"
    gate.save(model_file)
    reloaded = MemoryGateClassifier(model_path=model_file)
    assert reloaded.predict("我平时喝咖啡只喝无糖美式").label == "profile"


def test_embedder_blob_roundtrip_and_hybrid_retrieval():
    embedder = MemoryEmbedder(use_bge_if_cached=False)
    vec = embedder.encode("用户后端开发偏爱 FastAPI 框架")
    assert vec.shape == (512,)
    assert vec.dtype == np.float32
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-4

    blob = embedder.to_blob(vec)
    assert len(blob) == 2048
    assert np.allclose(vec, embedder.from_blob(blob))

    memories = [
        {
            "id": "m_fastapi",
            "layer": "episodic",
            "category": "preference",
            "content": "后端开发偏爱使用 FastAPI 与 Pydantic",
            "embedding_blob": embedder.to_blob(embedder.encode("后端开发偏爱使用 FastAPI 与 Pydantic")),
            "is_enabled": True,
            "is_pinned": False,
            "status": "active",
        },
        {
            "id": "m_coffee",
            "layer": "episodic",
            "category": "habit",
            "content": "每天早上喝一杯无糖冰美式咖啡",
            "embedding_blob": embedder.to_blob(embedder.encode("每天早上喝一杯无糖冰美式咖啡")),
            "is_enabled": True,
            "is_pinned": False,
            "status": "active",
        },
        {
            "id": "m_disabled",
            "layer": "episodic",
            "category": "preference",
            "content": "FastAPI 路由喜欢拆成单文件",
            "embedding_blob": embedder.to_blob(embedder.encode("FastAPI 路由喜欢拆成单文件")),
            "is_enabled": False,
            "is_pinned": False,
            "status": "active",
        },
    ]

    hits = embedder.retrieve(query="帮我用 FastAPI 写一个后端接口", memories=memories, top_k=2, threshold=0.15)
    hit_ids = [h["id"] for h in hits]
    assert "m_fastapi" in hit_ids
    assert "m_disabled" not in hit_ids
    assert hits[0]["id"] == "m_fastapi"
