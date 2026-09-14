from __future__ import annotations

import argparse
import json
import sys

from .analyzer import analyze_path


SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Zig 0.16 source code metrics.")
    parser.add_argument("path", help="Zig file or directory to analyze")
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--fail-on", choices=list(SEVERITY_ORDER), help="Exit non-zero if a finding at or above this severity exists")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = analyze_path(args.path)
    print(json.dumps(report, indent=2 if args.pretty else None, sort_keys=True))

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER.get(item["severity"], 0) >= threshold for item in report["findings"]):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
