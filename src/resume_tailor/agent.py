import threading

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


class Usage:
    """Running total of tokens and cost for every agent step in this process."""

    def __init__(self) -> None:
        self.calls = self.input_tokens = self.output_tokens = self.cache_tokens = 0
        self.cost_usd = 0.0
        self._lock = threading.Lock()  # resumes run in parallel threads

    def add(self, msg: ResultMessage) -> None:
        u = msg.usage or {}
        with self._lock:
            self.calls += 1
            self.input_tokens += u.get("input_tokens", 0)
            self.output_tokens += u.get("output_tokens", 0)
            self.cache_tokens += u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
            self.cost_usd += msg.total_cost_usd or 0.0

    def summary(self) -> str:
        return (f"Usage: {self.calls} calls, {self.input_tokens} in + {self.cache_tokens} cache / "
                f"{self.output_tokens} out tokens, ${self.cost_usd:.4f} (API-equivalent)")


usage = Usage()


async def _run(system: str, prompt: str, model: str | None) -> str:
    # tools=[] and setting_sources=[]: no tools, and no user hooks/CLAUDE.md leaking into the agent.
    options = ClaudeAgentOptions(
        system_prompt=system, tools=[], allowed_tools=[], setting_sources=[],
        max_turns=1, model=model, thinking={"type": "disabled"},
    )
    parts: list[str] = []
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            parts += [b.text for b in msg.content if isinstance(b, TextBlock)]
        elif isinstance(msg, ResultMessage):
            usage.add(msg)
            if msg.is_error:
                raise RuntimeError(f"Claude returned an error: {msg.result or msg.subtype}")
    return "".join(parts).strip()


def ask(system: str, prompt: str, model: str | None = None) -> str:
    """One agent step: a system prompt plus an input, no tools. Returns the text reply."""
    return anyio.run(_run, system, prompt, model)
