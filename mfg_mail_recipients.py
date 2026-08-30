# -*- coding: utf-8 -*-
"""Stałe odbiorcy kopii dla kampanii MFG (DE GU / Ost)."""
from __future__ import annotations

# Opcjonalny Cc biura — nie jest dodawany automatycznie (tylko przez MAIL_CC w .env).
MFG_OFFICE_CC_EMAIL = "office@mfg-fliesen.de"


def merge_mfg_campaign_cc(to_email: str, extra_env_cc: str = "") -> list[str]:
    """Widoczna kopia (Cc) — tylko z MAIL_CC w .env (bez automatycznego office@)."""
    try:
        from mail_transport import merge_mail_cc_recipients

        return merge_mail_cc_recipients(to_email, extra_env_cc)
    except Exception:
        return []
