from __future__ import annotations

import argparse
import asyncio

from flex_agent.config import DEFAULT_WORKSPACE
from flex_agent.ui.plain_cli import run_plain_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="flex-agent interactive open coding CLI")
    parser.add_argument(
        "--workspace",
        default=str(DEFAULT_WORKSPACE),
        help="Workspace directory for persistent coding files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(run_plain_cli(workspace_path=args.workspace))


if __name__ == "__main__":
    raise SystemExit(main())
