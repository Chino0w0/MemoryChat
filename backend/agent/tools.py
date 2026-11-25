from __future__ import annotations

from typing import Any, Callable


class ToolRegistry:
    """Extensible registry for built-in memory tools and Phase 2 external tools."""

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._schemas[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._handlers[name] = handler

    def list_schemas(self) -> list[dict[str, Any]]:
        return list(self._schemas.values())

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name not in self._handlers:
            raise KeyError(f"Unregistered tool: {name}")
        return self._handlers[name](args)
