from __future__ import annotations

"""
Standalone training & evaluation script for Plan A Small Model #1 (MemoryGate).
Supports both Baidu DuLeMon JSONL files (placed under ml_experiments/data/)
and the built-in bootstrap corpus for instant sanity verification.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sklearn.metrics import classification_report  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from app.ml.memory_gate import BOOTSTRAP_CORPUS, GateLabel, MemoryGateClassifier  # noqa: E402


def load_dulemon_or_bootstrap(data_path: Path | None) -> tuple[list[str], list[GateLabel]]:
    if data_path and data_path.exists():
        texts: list[str] = []
        labels: list[GateLabel] = []
        for line in data_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            text = str(row.get("text") or "").strip()
            label = row.get("label")
            if text and label in {"skip", "profile", "episodic"}:
                texts.append(text)
                labels.append(label)
        if texts:
            return texts, labels

    texts_b, labels_b = zip(*BOOTSTRAP_CORPUS)
    return list(texts_b), list(labels_b)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate MemoryGate 3-class small model")
    parser.add_argument("--data", type=Path, default=None, help="Optional JSONL dataset path (text, label)")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "backend" / "data" / "memory_gate.joblib",
        help="Output .joblib weight path",
    )
    args = parser.parse_args()

    texts, labels = load_dulemon_or_bootstrap(args.data)
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )

    clf = MemoryGateClassifier(threshold=0.40)
    clf.fit(x_train, y_train)
    preds = [clf.predict(t).label for t in x_test]
    print(classification_report(y_test, preds, digits=3, zero_division=0))

    clf.fit(texts, labels)
    clf.save(args.out)
    print(f"Saved trained MemoryGate weights -> {args.out}")


if __name__ == "__main__":
    main()
