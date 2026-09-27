"""System prompts for LLM-backed agents, kept as Markdown so they are easy to tune."""

from functools import cache
from importlib import resources


@cache
def load_prompt(name: str) -> str:
    return (resources.files(__package__) / f"{name}.md").read_text(encoding="utf-8").strip()
