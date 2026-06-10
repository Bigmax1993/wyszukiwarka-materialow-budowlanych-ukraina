# -*- coding: utf-8 -*-
"""GHA: czy sobota ma kontynuowac discovery po piatku (exit 0=tak, 1=nie)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from discovery_run_state import (  # noqa: E402
    discovery_run_state_summary,
    discovery_should_continue_saturday,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache",
        default="Wyniki/de_gu_bauunternehmen_cache.json",
        help="Sciezka do cache JSON z artefaktu piatku",
    )
    args = parser.parse_args()
    path = Path(args.cache)
    if not path.is_file():
        print(f"Brak cache: {path}", file=sys.stderr)
        return 1
    cache = json.loads(path.read_text(encoding="utf-8"))
    summary = discovery_run_state_summary(cache)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if discovery_should_continue_saturday(cache):
        print("KONTYNUUJ: Serper w piatek nie wyczerpany / cel nie osiagniety.")
        return 0
    print("POMIN: piatek wyczerpal Serper lub osiagnal cel discovery.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
