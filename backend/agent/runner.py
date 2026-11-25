from __future__ import annotations

from typing import Any, Iterator

from agent.skills import SkillLoader
from agent.tools import ToolRegistry
from llm.provider import MultiProviderClient


class AgentRunner:
    """Lightweight streaming turn runner with progressive SKILL.md injection and tool hooks."""

    def __init__(self, llm: MultiProviderClient, skills: SkillLoader, tools: ToolRegistry):
        self.llm = llm
        self.skills = skills
        self.tools = tools

    def build_augmented_system_prompt(self, base_system_prompt: str, active_skills: list[str] | None = None) -> str:
        sections = [base_system_prompt]
        for skill_name in active_skills or []:
            body = self.skills.load_skill_body(skill_name)
            if body:
                sections.append(f"<active_skill name=\"{skill_name}\">\n{body}\n</active_skill>")
        return "\n\n".join(sections)

    def stream_turn(
        self,
        provider: dict[str, Any],
        model: str,
        system_prompt: str,
        history: list[dict[str, str]],
        user_content: str,
        active_skills: list[str] | None = None,
    ) -> Iterator[str]:
        final_sys = self.build_augmented_system_prompt(system_prompt, active_skills=active_skills)
        messages: list[dict[str, Any]] = [{"role": "system", "content": final_sys}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_content})
        yield from self.llm.stream_chat(provider=provider, model=model, messages=messages)
