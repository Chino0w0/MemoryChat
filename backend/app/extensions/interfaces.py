from __future__ import annotations

from typing import Any, Protocol


class VoiceAdapter(Protocol):
    """Reserved Phase 2 slot for lightweight ASR / TTS voice input-output."""

    name: str

    def transcribe(self, audio_bytes: bytes, mime_type: str) -> str: ...


class SkillPlugin(Protocol):
    """Reserved Phase 2 slot for Pi/DSH-compatible SKILL.md progressive disclosure."""

    name: str
    description: str

    def load_instructions(self) -> str: ...


class AgentTool(Protocol):
    """Reserved Phase 2 slot for Function Calling tools."""

    name: str
    schema: dict[str, Any]

    def execute(self, args: dict[str, Any]) -> dict[str, Any]: ...


class ExtensionRegistry:
    """Maintains extension slots so ASR, Skills, and Tools plug in cleanly in Phase 2."""

    def __init__(self) -> None:
        self._voice: dict[str, VoiceAdapter] = {}
        self._skills: dict[str, SkillPlugin] = {}
        self._tools: dict[str, AgentTool] = {}

    def register_voice(self, adapter: VoiceAdapter) -> None:
        self._voice[adapter.name] = adapter

    def register_skill(self, skill: SkillPlugin) -> None:
        self._skills[skill.name] = skill

    def register_tool(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def list_slots(self) -> list[dict[str, Any]]:
        return [
            {
                "slot": "asr",
                "label": "Voice / ASR",
                "status": "active" if self._voice else "reserved",
                "count": len(self._voice),
            },
            {
                "slot": "skill",
                "label": "SKILL.md Plugins",
                "status": "active" if self._skills else "reserved",
                "count": len(self._skills),
            },
            {
                "slot": "tool",
                "label": "Agent Tools",
                "status": "active" if self._tools else "reserved",
                "count": len(self._tools),
            },
        ]
