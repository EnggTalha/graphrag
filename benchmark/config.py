"""Benchmark configuration resolved from CLI args and environment variables."""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

ALL_MODES = ("vector", "graph", "hybrid")


@dataclass
class BenchmarkConfig:
    backends: List[str]
    llms: List[str]
    modes: List[str]
    questions_path: str
    output_path: str
    limit: int
    text_weight: float
    load_from_pg: bool
    max_questions: Optional[int] = None
    dimension: int = field(default=384)


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def resolve_config(args) -> BenchmarkConfig:
    """Merge CLI args with env defaults into a single config object."""
    backends = args.backends or _split_csv(os.getenv("VECTOR_BACKEND")) or ["pgvector"]
    llms = args.llms or _split_csv(os.getenv("BENCHMARK_LLMS")) or _split_csv(
        os.getenv("LLM_CHOICE")
    ) or ["mistral"]
    modes = args.modes or list(ALL_MODES)

    for m in modes:
        if m not in ALL_MODES:
            raise ValueError(f"Unknown mode '{m}'. Valid: {', '.join(ALL_MODES)}")

    limit = args.limit if args.limit is not None else int(os.getenv("BENCHMARK_LIMIT", "5"))
    dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    return BenchmarkConfig(
        backends=backends,
        llms=llms,
        modes=modes,
        questions_path=args.questions,
        output_path=args.output,
        limit=limit,
        text_weight=args.text_weight,
        load_from_pg=args.load_from_pg,
        max_questions=args.max_questions,
        dimension=dimension,
    )
