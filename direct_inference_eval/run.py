from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from direct_eval.pipeline import run_experiment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run self-contained direct inference baseline and CPR evaluation.",
    )
    parser.add_argument(
        "--input",
        default="data/codebook_done_human.jsonl",
        help="JSONL input with comments and human benchmark labels.",
    )
    parser.add_argument(
        "--output",
        default="direct_inference_eval/runs/default",
        help="Output run directory.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of comments per direct inference LLM call.",
    )
    parser.add_argument(
        "--mode",
        choices=("open", "axial", "both"),
        default="both",
        help="Which evaluation report(s) to generate.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of input records to process.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override OPENAI_MODEL for direct inference and semantic eval.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse complete batch_*.json prediction files.",
    )
    parser.add_argument(
        "--no-llm-semantic",
        action="store_true",
        help="Skip optional LLM semantic alignment sections in reports.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_experiment(
        input_path=Path(args.input),
        output_dir=Path(args.output),
        batch_size=args.batch_size,
        mode=args.mode,
        limit=args.limit,
        model=args.model,
        resume=args.resume,
        run_llm_semantic=not args.no_llm_semantic,
    )
    print(f"Predictions: {result['records_path']}")
    for report_path in result["reports"]:
        print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
