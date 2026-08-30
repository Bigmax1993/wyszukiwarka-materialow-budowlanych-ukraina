# -*- coding: utf-8 -*-
"""Eksport aktualnej prezentacji MFG ze Slides → PPTX (runner GHA / lokalnie)."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mfg_gu_email_attachment import (  # noqa: E402
    ATTACHMENT_FILENAME,
    GOOGLE_SLIDES_URL,
    _download_slides_pptx,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export MFG Slides → PPTX")
    parser.add_argument(
        "--dest",
        default=str(ROOT / "assets" / "campaign" / ATTACHMENT_FILENAME),
        help="Docelowa ścieżka PPTX",
    )
    args = parser.parse_args()
    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("export_mfg_slides")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not _download_slides_pptx(dest, logger):
        print(
            f"BLAD: nie pobrano PPTX ze Slides ({GOOGLE_SLIDES_URL}). "
            "Sprawdz GDRIVE_OAUTH_* lub udostepnienie prezentacji.",
            file=sys.stderr,
        )
        return 1
    print(f"OK: {dest} ({dest.stat().st_size / (1024 * 1024):.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
