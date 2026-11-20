"""
Command-line entry point for the benchmark.

Examples:
    # Compare vector DBs (loads the same pgvector chunks into each), all modes:
    python -m benchmark --backends pgvector qdrant chroma --load-from-pg \
        --llms mistral --output results/comparison_summary.csv

    # Compare multiple LLMs on the default backend:
    python -m benchmark --llms mistral llama3

Run `python -m benchmark --help` for all options.
"""

import argparse
import asyncio
import logging
import sys

from benchmark.config import resolve_config
from benchmark.questions import DEFAULT_QUESTIONS_PATH
from benchmark.runner import run_benchmark


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m benchmark",
        description="Benchmark vector DB backends and LLMs over an evaluation question set.",
    )
    p.add_argument(
        "--backends",
        nargs="+",
        choices=["pgvector", "qdrant", "chroma"],
        help="Vector DB backends to test, one at a time (default: $VECTOR_BACKEND or pgvector).",
    )
    p.add_argument(
        "--llms",
        nargs="+",
        help="LLM model names to compare (default: $BENCHMARK_LLMS, then $LLM_CHOICE, then mistral).",
    )
    p.add_argument(
        "--modes",
        nargs="+",
        choices=["vector", "graph", "hybrid"],
        help="Retrieval modes to run (default: vector graph hybrid).",
    )
    p.add_argument(
        "--questions",
        default=DEFAULT_QUESTIONS_PATH,
        help=f"Path to evaluation questions JSON (default: {DEFAULT_QUESTIONS_PATH}).",
    )
    p.add_argument(
        "--output",
        default="results/comparison_summary.csv",
        help="Output CSV path (default: results/comparison_summary.csv).",
    )
    p.add_argument(
        "--limit", type=int, default=None, help="Max results per retrieval (default: 5)."
    )
    p.add_argument(
        "--text-weight",
        type=float,
        default=0.3,
        help="Hybrid search text weight 0-1 (default: 0.3).",
    )
    p.add_argument(
        "--load-from-pg",
        action="store_true",
        help="Copy embedded chunks from pgvector into the selected backend before querying "
        "(ensures the same chunks run against each DB). No-op for pgvector.",
    )
    p.add_argument(
        "--max-questions",
        type=int,
        default=None,
        help="Only use the first N questions (useful for quick runs).",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO).",
    )
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = resolve_config(args)
    output = asyncio.run(run_benchmark(config))
    print(f"\nBenchmark complete. Results written to: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
