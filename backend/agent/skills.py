from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class SkillLoader:
    """Scans skills/*/SKILL.md using progressive disclosure (Pi / DSH compatible)."""

    def __init__(self, skills_root: str | Path):
        self.skills_root = Path(skills_root)

    def list_skills(self) -> list[dict[str, str]]:
        if not self.skills_root.exists():
            return []
        results: list[dict[str, str]] = []
        for skill_md in sorted(self.skills_root.glob("*/SKILL.md")):
            meta = self._parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            name = meta.get("name") or skill_md.parent.name
            desc = meta.get("description") or ""
            results.append({"name": name, "description": desc, "path": str(skill_md)})
        return results

    def load_skill_body(self, name: str) -> str | None:
        target = self.skills_root / name / "SKILL.md"
        if not target.exists():
            return None
        raw = target.read_text(encoding="utf-8")
        return re.sub(r"^---\s*\n.*?\n---\s*\n?", "", raw, count=1, flags=re.DOTALL).strip()

    @staticmethod
    def _parse_frontmatter(raw: str) -> dict[str, Any]:
        match = re.match(r"^---\s*\n(.*?)\n---", raw, flags=re.DOTALL)
        if not match:
            return {}
        meta: dict[str, Any] = {}
        for line in match.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
        return meta
