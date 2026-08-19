# -*- coding: utf-8 -*-
"""Odzyskaj contacts z uszkodzonego cache JSON (ucięty przy zapisie artefaktu GHA)."""
from __future__ import annotations

import json
import re
from pathlib import Path


def recover_contacts_from_cache_file(path: Path) -> dict[str, dict]:
    """Zwraca dict contacts z pliku cache (pełny lub częściowo uszkodzony)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
        contacts = data.get("contacts") or {}
        return contacts if isinstance(contacts, dict) else {}
    except json.JSONDecodeError:
        pass

  # Ucięty zapis: website_crawl z ogromnym page_text — obetnij przed tym kluczem.
    m = re.search(r'\n  "website_crawl"\s*:\s*\{', raw)
    if m:
        prefix = raw[: m.start()].rstrip()
        if prefix.endswith(","):
            prefix = prefix[:-1]
        repaired = prefix + "\n}"
        try:
            data = json.loads(repaired)
            contacts = data.get("contacts") or {}
            return contacts if isinstance(contacts, dict) else {}
        except json.JSONDecodeError:
            pass

    # Fallback: wyciągnij tylko blok contacts { ... } na początku pliku.
    m2 = re.search(r'"contacts"\s*:\s*\{', raw)
    if not m2:
        return {}
    start = m2.end() - 1
    depth = 0
    end = None
    for i in range(start, len(raw)):
        ch = raw[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return {}
    blob = "{" + raw[start:end] + "}"
    try:
        contacts = json.loads(blob)
        return contacts if isinstance(contacts, dict) else {}
    except json.JSONDecodeError:
        return {}


def recover_contacts_from_run_artifact(
    run_id: str,
    *,
    repo: str,
    dest: Path,
) -> dict[str, dict]:
    import subprocess

    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "-R",
            repo,
            "-n",
            "de-gu-wyniki-pi",
            "-D",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Nie pobrano artefaktu pi z run {run_id}: "
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    cache_path = dest / "Wyniki" / "de_gu_bauunternehmen_cache.json"
    if not cache_path.is_file():
        raise RuntimeError(f"Brak cache w artefakcie run {run_id}")
    return recover_contacts_from_cache_file(cache_path)
