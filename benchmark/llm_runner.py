"""
Multi-LLM generation benchmarking.

Builds a prompt from the SAME retrieved context for each model, runs the model, and records
generation latency, token usage, and the answer. Reuses the project's existing
OpenAI-compatible model wiring (Ollama local models and OpenAI-compatible APIs).
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a precise assistant. Answer the user's question using ONLY the provided "
    "context when it is relevant. If the context does not contain the answer, say so "
    "briefly and answer from general knowledge. Be concise."
)

# Cache one agent per model name to avoid rebuilding on every call.
_agent_cache: Dict[str, Any] = {}


@dataclass
class GenerationResult:
    answer: str = ""
    generation_latency_ms: float = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    error: str = ""


def _get_agent(model_name: str):
    if model_name in _agent_cache:
        return _agent_cache[model_name]
    from pydantic_ai import Agent

    from agent.providers import get_llm_model

    agent = Agent(get_llm_model(model_name), system_prompt=SYSTEM_PROMPT)
    _agent_cache[model_name] = agent
    return agent


def build_prompt(question: str, context: str) -> str:
    if context.strip():
        return (
            "[CONTEXT]\n"
            f"{context}\n\n"
            "[QUESTION]\n"
            f"{question}\n\n"
            "Answer the question using the context above where relevant."
        )
    return (
        "[QUESTION]\n"
        f"{question}\n\n"
        "No retrieval context was available; answer from general knowledge."
    )


def _extract_usage(result: Any) -> Dict[str, Optional[int]]:
    """
    Extract token usage from a pydantic-ai run result, defensively across versions.

    Different versions name the fields differently (request/response vs input/output).
    Returns prompt/completion/total as ints when available, else None.
    """
    prompt = completion = total = None
    try:
        usage = result.usage() if callable(getattr(result, "usage", None)) else None
    except Exception:  # noqa: BLE001
        usage = None
    if usage is None:
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}

    def pick(*names):
        for n in names:
            v = getattr(usage, n, None)
            if isinstance(v, int):
                return v
        return None

    prompt = pick("request_tokens", "input_tokens", "prompt_tokens")
    completion = pick("response_tokens", "output_tokens", "completion_tokens")
    total = pick("total_tokens")
    if total is None and (prompt is not None or completion is not None):
        total = (prompt or 0) + (completion or 0)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


async def generate(question: str, context: str, model_name: str) -> GenerationResult:
    """Run one model on one (question, context) pair and record metrics."""
    prompt = build_prompt(question, context)
    start = time.perf_counter()
    try:
        agent = _get_agent(model_name)
        result = await agent.run(prompt)
        elapsed = (time.perf_counter() - start) * 1000.0
        answer = getattr(result, "output", None)
        if answer is None:
            answer = getattr(result, "data", "")
        usage = _extract_usage(result)
        return GenerationResult(
            answer=str(answer),
            generation_latency_ms=elapsed,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
        )
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.warning("Generation failed for model '%s': %s", model_name, exc)
        return GenerationResult(generation_latency_ms=elapsed, error=str(exc))
