"""Generate and verify the committed JSON Schemas.

Schemas are generated from the models and committed, because non-Python
consumers, mock authors and reviewers need to read the shape without running the
code — and a schema that can drift from its model is worse than no schema. CI
runs ``--check``; any divergence fails the build.

Usage:
    python -m oncokernel_contracts.schemas          # regenerate
    python -m oncokernel_contracts.schemas --check  # fail on drift
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from oncokernel_contracts.profiles import GenomicProfile, PseudonymizedProfile

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

MODELS: tuple[type[BaseModel], ...] = (GenomicProfile, PseudonymizedProfile)


def _render(model: type[BaseModel]) -> str:
    return json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"


def _path_for(model: type[BaseModel]) -> Path:
    return SCHEMA_DIR / f"{model.__name__}.schema.json"


def write() -> list[Path]:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for model in MODELS:
        path = _path_for(model)
        path.write_text(_render(model), encoding="utf-8")
        written.append(path)
    return written


def check() -> list[str]:
    """Return a list of drift descriptions; empty means clean."""
    problems = []
    for model in MODELS:
        path = _path_for(model)
        if not path.exists():
            problems.append(f"missing: {path.name}")
            continue
        if path.read_text(encoding="utf-8") != _render(model):
            problems.append(f"out of date: {path.name}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed schemas match the models instead of rewriting them",
    )
    args = parser.parse_args()

    if args.check:
        problems = check()
        if problems:
            print("JSON Schema drift detected:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            print(
                "\nRun: python -m oncokernel_contracts.schemas",
                file=sys.stderr,
            )
            return 1
        print(f"schemas up to date ({len(MODELS)} models)")
        return 0

    for path in write():
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
