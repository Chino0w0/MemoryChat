from __future__ import annotations

"""
Downloads or converts Baidu DuLeMon (Chinese Long-Term Persona Dialogue Dataset)
into standardized JSONL rows {"text": ..., "label": "skip"|"profile"|"episodic"}
under ml_experiments/data/dulemon_gate.jsonl.
"""

import argparse
import json
from pathlib import Path

EPISODIC_KEYWORDS = ("最近", "下周", "明天", "打算", "准备", "正在", "月底", "周末", "计划", "截止")


def convert_raw_dulemon(raw_dir: Path, out_file: Path) -> int:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_file.open("w", encoding="utf-8") as fw:
        for fp in sorted(raw_dir.glob("*.json*")):
            for line in fp.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                personas = obj.get("user_persona") or obj.get("persona") or []
                for p in personas:
                    text = str(p).strip()
                    if not text:
                        continue
                    label = "episodic" if any(k in text for k in EPISODIC_KEYWORDS) else "profile"
                    fw.write(json.dumps({"text": text, "label": label}, ensure_ascii=False) + "\n")
                    count += 1
                for turn in obj.get("conversation", []):
                    utt = str(turn.get("utterance") or turn.get("text") or "").strip()
                    has_grounding = bool(turn.get("persona_grounding") or turn.get("label"))
                    if utt and not has_grounding:
                        fw.write(json.dumps({"text": utt, "label": "skip"}, ensure_ascii=False) + "\n")
                        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare DuLeMon JSONL for MemoryGate training")
    parser.add_argument("--raw-dir", type=Path, default=Path(__file__).parent / "data" / "raw")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "data" / "dulemon_gate.jsonl")
    args = parser.parse_args()

    if not args.raw_dir.exists():
        print(f"Place extracted DuLeMon JSON/JSONL files in: {args.raw_dir}")
        return
    total = convert_raw_dulemon(args.raw_dir, args.out)
    print(f"Wrote {total} labeled samples -> {args.out}")


if __name__ == "__main__":
    main()
