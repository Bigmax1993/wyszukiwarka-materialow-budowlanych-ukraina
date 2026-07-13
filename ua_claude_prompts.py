# -*- coding: utf-8 -*-
"""Prompty Claude — kampania UA: hurtownie materiałów budowlanych."""
from __future__ import annotations

import re

from ua_campaign_keyword_profile import (
    SERPER_TEMPLATE_PATTERNS,
    gu_required_keywords_sample,
    large_company_markers_sample,
    negative_keywords_sample,
    retail_chain_keywords_sample,
    retail_context_keywords_sample,
    small_company_markers_sample,
)

_REQUIRED_MATERIALS = "цемент, пісок, щебінь, цегла, блок, арматура, утеплювач, плитка, гіпсокартон"
PAGE_VERIFY_MAX_CHARS = 18000
CONTACT_EXTRACT_MAX_CHARS = 16000
_CONTACT_EXTRACT_TEXT_PRIORITY = (
    "контакт",
    "kontakt",
    "contact",
    "mailto",
    "@",
    "тел",
    "телефон",
    "phone",
    "email",
    "e-mail",
    "адреса",
)
_PAGE_VERIFY_TEXT_PRIORITY = (
    "будматеріали",
    "будівельні",
    "каталог",
    "асортимент",
    "продукція",
    "прайс",
    "ціни",
    "опт",
    "склад",
    "доставка",
    "цемент",
    "пісок",
    "щебінь",
    "цегла",
    "утеплювач",
    "плитка",
)


def prioritize_page_text_for_verify(
    page_text: str,
    *,
    max_chars: int = PAGE_VERIFY_MAX_CHARS,
    priority_keywords: tuple[str, ...] | None = None,
) -> str:
    keys = priority_keywords or _PAGE_VERIFY_TEXT_PRIORITY
    raw = (page_text or "").strip()
    if len(raw) <= max_chars:
        return raw
    if "=== http" in raw:
        sections = re.split(r"(?=\n=== https?://)", "\n" + raw)
        sections = [s.strip() for s in sections if s.strip()]
        priority_sec: list[str] = []
        other_sec: list[str] = []
        for sec in sections:
            low = sec.lower()
            if any(k in low for k in keys):
                priority_sec.append(sec)
            else:
                other_sec.append(sec)
        merged = "\n\n".join(priority_sec + other_sec)
    else:
        lines = [ln.strip() for ln in re.split(r"[\n\r]+", raw) if ln.strip()]
        if not lines:
            return raw[:max_chars]
        priority: list[str] = []
        other: list[str] = []
        for ln in lines:
            low = ln.lower()
            if any(k in low for k in keys):
                priority.append(ln)
            else:
                other.append(ln)
        merged = " ".join(priority + other)
    if len(merged) <= max_chars:
        return merged
    return merged[: max_chars - 3] + "..."


def build_contact_extract_prompt_pl(
    company_name: str,
    website: str,
    page_text: str,
    *,
    regex_candidates: list[str] | None = None,
    impressum_candidates: list[str] | None = None,
    regex_phones: list[str] | None = None,
    extra_context: str = "",
) -> str:
    """
    Prompt PL dla ekstrakcji kontaktów UA (hurtownie budowlane).
    Uwzględnia kandydatów z regex, gdy scoring ich nie wybrał.
    """
    from claude_page_text import build_claude_context_header, extract_crawl_section_urls

    raw = page_text or ""
    header = build_claude_context_header(
        company_name,
        website,
        pages_crawled=max(raw.count("=== http"), 1 if raw else 0),
        priority_urls=extract_crawl_section_urls(raw),
    )
    snippet = prioritize_page_text_for_verify(
        raw,
        max_chars=CONTACT_EXTRACT_MAX_CHARS,
        priority_keywords=_CONTACT_EXTRACT_TEXT_PRIORITY,
    )
    regex_lines = [
        e.strip()
        for e in (regex_candidates or [])
        if (e or "").strip() and "@" in e
    ]
    impressum_lines = [
        e.strip()
        for e in (impressum_candidates or [])
        if (e or "").strip() and "@" in e
    ]
    phone_lines = [p.strip() for p in (regex_phones or []) if (p or "").strip()]
    regex_block = (
        "\n".join(f"- {e}" for e in regex_lines)
        if regex_lines
        else "(brak — szukaj wyłącznie w tekście strony)"
    )
    impressum_block = (
        "\n".join(f"- {e}" for e in impressum_lines)
        if impressum_lines
        else "(brak)"
    )
    phones_block = (
        "\n".join(f"- {p}" for p in phone_lines)
        if phone_lines
        else "(brak)"
    )
    extra = (extra_context or "").strip()
    if len(extra) > 2500:
        extra = extra[:2497] + "..."
    return f"""ROLA
Jesteś analitykiem kontaktów B2B dla hurtowni i składów materiałów budowlanych na Ukrainie.
Twoje jedyne zadanie: wskazać najlepszy e-mail do zapytania ofertowego oraz telefony firmy.

KONTEKST
{header}

KANDYDACI Z REGEX (system ich nie wybrał do wysyłki — zweryfikuj, wybierz najlepszy LUB znajdź inny w tekście)
{regex_block}

KANDYDACI Z IMPRESSUM / KONTAKT (regex)
{impressum_block}

TELEFONY ZNALEZIONE PRZEZ REGEX
{phones_block}

DODATKOWY KONTEKST (Serper, weryfikacja, fragment strony)
{extra or "(brak)"}

ZASADY (ścisłe)
• Wyciągaj wyłącznie dane obecne DOSŁOWNIE w tekście strony LUB na listach REGEX powyżej.
• Jeśli REGEX znalazł sensowny e-mail firmowy (także gmail.com, ukr.net, i.ua) — UMIEŚĆ go w emails
  (możesz wybrać najlepszy z listy REGEX, nie musisz znajdować innego).
• Priorytet stron: /контакти, /kontakt, /contact, impressum, o firmie.
• Telefony UA: +380 lub format 0XX… (komórka/stacjonarny); max 3 unikalne numery.
• Odrzuć: noreply, no-reply, privacy, newsletter, rekrutacja, portale (instagram, facebook).
• Local-part (przed @): 1–50 znaków.
• Gdy crawl jest ubogi (WAF, Cloudflare, mało tekstu) — oprzyj się na REGEX + dodatkowym kontekście.
• Niczego nie wymyślaj — jeśli brak danych, zwróć puste listy.

WYJŚCIE (wyłącznie JSON, bez markdown)
{{"company_name":"","emails":[],"phones":[],"impressum_emails":[],"reason":""}}

Pola:
• company_name — oficjalna nazwa firmy tylko gdy jasno w kontakcie/impressum, inaczej ""
• emails — wszystkie sensowne e-maile firmowe (w tym wybrane z REGEX)
• impressum_emails — podzbiór emails ze stron kontakt/impressum/legal
• phones — max 3 unikalne numery UA
• reason — max 1 zdanie po polsku (np. „Wybrano venbud.dealer@gmail.com z regex" lub „Brak kontaktu w tekście")

FRAGMENT STRONY (crawl domeny)
{snippet or "(pusty lub zablokowany przez WAF — użyj REGEX i kontekstu powyżej)"}
"""


def build_page_verify_prompt(
    company_name: str,
    website: str,
    page_text: str,
    *,
    max_chars: int = PAGE_VERIFY_MAX_CHARS,
    serper_blob: str = "",
    pages_crawled: int = 0,
) -> str:
    from claude_page_text import (
        build_automatic_evidence_excerpt,
        build_claude_context_header,
        extract_crawl_section_urls,
    )

    raw = page_text or ""
    priority_urls = extract_crawl_section_urls(raw)
    header = build_claude_context_header(
        company_name,
        website,
        serper_blob=serper_blob,
        pages_crawled=pages_crawled or max(raw.count("=== http"), 1 if raw else 0),
        priority_urls=priority_urls,
    )
    evidence = build_automatic_evidence_excerpt(raw)
    snippet = prioritize_page_text_for_verify(raw, max_chars=max_chars)
    supplier_kw = ", ".join(gu_required_keywords_sample())
    material_kw = ", ".join(retail_context_keywords_sample())
    category_kw = ", ".join(retail_chain_keywords_sample())
    neg_kw = ", ".join(negative_keywords_sample())
    small_kw = ", ".join(small_company_markers_sample())
    large_kw = ", ".join(large_company_markers_sample())
    return f"""РОЛЬ
Ти — аналітик B2B для пошуку ГУРТОВЕНЬ (оптових постачальників) будівельних матеріалів в Україні.
Ціль ЛИШЕ: гуртівні / оптові бази / оптові склади / оптові дистриб'ютори будматеріалів, а також виробники з оптовим продажем — ЗАВЖДИ з базою в Україні.
НЕ ціль: суто роздрібні магазини без опту, портали новин, держустанови, чисті підрядники без продажу матеріалів, оголошення OLX, фірми поза Україною.

ЗАВДАННЯ
Прочитай витяг сайту (усі підсторінки, позначені «=== URL ===»).
Чи це ГУРТОВНЯ (оптовий постачальник) будматеріалів В УКРАЇНІ? Відповідай ЛИШЕ JSON — без markdown.

ЩО ВВАЖАЄТЬСЯ ДОКАЗОМ (потрібні ОБИДВІ умови)
1. ОПТ/ГУРТ: слова «опт», «оптом», «оптовий», «оптова база», «гурт», «гуртовий», «гуртові ціни», «оптова торгівля», «B2B», «оптовий склад», «постачання зі складу», прайс для оптових/дилерів.
2. БУДМАТЕРІАЛИ: категорії {_REQUIRED_MATERIALS}; роль — оптовий постачальник, виробник з оптом, дистриб'ютор, будівельна база.
+ Локація в Україні: домен .ua, адреса в Україні, телефон +380, згадка міст/областей України.

ВІДХИЛИТИ (is_gu=false / has_retail_context=false)
• СУТО РОЗДРІБНИЙ магазин / будмаркет для кінцевого покупця без опту (немає «опт/гурт/оптові ціни/B2B»)
• Фірма поза Україною (домен/адреса/телефон не українські)
• Архітектурне бюро, дизайн інтер'єру, ремонт квартир без продажу матеріалів
• Новини, медіа, держоргани, банки, вакансії без комерційної пропозиції
• OLX/оголошення б/у без стабільного бізнесу постачальника

ПОЛЯ JSON (ті самі ключі для сумісності з pipeline)
• is_gu = true ЛИШЕ якщо це оптова гуртівня/оптовий постачальник/виробник з оптом будматеріалів в Україні
• has_retail_context = true ЛИШЕ якщо є ОПТОВА комерційна пропозиція (опт, гурт, оптові/дилерські ціни, склад для B2B) — суто роздріб = false
• matched_chains = категорії матеріалів з тексту (цемент, пісок, …) — лише якщо згадані
• is_small_firm = регіональна/мала фірма (не велика міжнародна мережа)

МАЛІ ОЗНАКИ: {small_kw}
ВЕЛИКІ ОЗНАКИ (is_small_firm=false): {large_kw}

КЛЮЧОВІ СЛОВА ПОСТАЧАЛЬНИКА: {supplier_kw}
КОНТЕКСТ МАТЕРІАЛІВ: {material_kw}
КАТЕГОРІЇ: {category_kw}
НЕГАТИВ: {neg_kw}

СХЕМА JSON
{{
  "matched_gu_keywords": [],
  "matched_retail_keywords": [],
  "matched_chains": [],
  "matched_negative_keywords": [],
  "is_gu": false,
  "has_retail_context": false,
  "is_small_firm": false,
  "primary_role": "",
  "reason": ""
}}

КОНТЕКСТ
{header}

АВТОДОКАЗИ
{evidence}

ВИТЯГ САЙТУ
{snippet or "(порожньо)"}
"""


def build_row_cleanup_prompt(
    *,
    company: str,
    address: str,
    phone: str,
    email: str,
    website: str,
    states: str,
    handelsketten: str = "",
    url: str = "",
) -> str:
    return f"""РОЛЬ
Ти — QA-фільтр перед експортом у Excel (kolumna «Adres», telefon, website).
Будь безжальним: краще porozhne pole "", nizh bрехня w adresie.

ВАЖЛИВО: company_name_clean ЗАВЖДИ повертaj як "".
Kolumna «Nazwa firmy» jest ZAWSZE ustawiana przez system wyłącznie z domeny website
(np. wikibud.com.ua → Wikibud). Nie wypełniaj company_name_clean.

ВІДПОВІДЬ — ЛИШЕ JSON (без markdown, без пояснень).

СХЕМА (усі ключі обов'язкові)
{{"company_name_clean":"","address":"","phone":"","website":"","bundesland":"","handelsketten":"","url":""}}

═══════════════════════════════════════════════════════════
company_name_clean
═══════════════════════════════════════════════════════════
ЗАВЖДИ "" — ignoruj pole company.

═══════════════════════════════════════════════════════════
address — KILLER-ПРАВИЛА
═══════════════════════════════════════════════════════════

ДОЗВОЛЕНО:
• Фізична адреса в Україні: вулиця/проспект/провулок + (будинок) + місто (+ область).
• Приклади OK:
  «вул. Промислова, 12, м. Київ»
  «просп. Перемоги, 45, Львів, Львівська обл.»
  «с. Гатне, вул. Центральна, 3, Київська обл.»

ЗАБОРОНЕНО — address = "":
• Лише «Київ», «Україна», «Київська область» без вулиці
• Маркетинг / опис асортименту / слогани (те саме що в company)
• Ціни, товари, «грн/м», «від … грн»
• «біля метро …», «доставка по Україні» без вулиці
• Дубль назви фірми або домену
• Текст довший за ~120 символів без ознак вулиці (вул., ул., просп., пров., бульв., наб., пл., буд., оф.)

ПРАВИЛО: немає вулиці (вул./ул./просп./пров./бульв./наб.) → address = ""
(виняток: с./смт. + вул. — OK)

═══════════════════════════════════════════════════════════
Інші поля
═══════════════════════════════════════════════════════════
• phone — один номер UA (+380… або 0XX…) або ""
• website — https://domain.tld (корінь, без шляху /search /product) або ""
• url — ідентично website
• bundesland — РІВНО один з: [{states}] — інакше ""
• handelsketten — категорії матеріалів малими літерами через кому (цемент, пісок, …) або ""
• email — НЕ виходить у JSON; лише для перевірки

═══════════════════════════════════════════════════════════
НЕГАТИВНІ ПРИКЛАДИ (еталон поведінки)
═══════════════════════════════════════════════════════════
company="Фольгований утеплювач", website="https://wikibud.com.ua", address="Київ"
→ {{"company_name_clean":"","address":"","phone":"…","website":"https://wikibud.com.ua","bundesland":"Київ","handelsketten":"…","url":"https://wikibud.com.ua"}}

company="Service unavailable", address="Київ"
→ company_name_clean="", address=""

company="budMATERIAL: Купити будівельні матерія", website="https://budmaterial.kyiv.ua", address="Рішення просте — замовте…"
→ company_name_clean="", address=""

company="ТОВ \"Венбуд\"", website="https://venbud.ua", address="м. Київ, вул. Бориспільська, 1"
→ company_name_clean="", address="вул. Бориспільська, 1, м. Київ"

═══════════════════════════════════════════════════════════
ВХІД (сирий скрап — не довіряй сліпо)
═══════════════════════════════════════════════════════════
company={company!r}
address={address!r}
phone={phone!r}
email={email!r}
website={website!r}
handelsketten={handelsketten!r}
url={url!r}
"""


def build_personalized_inquiry_email_prompt_uk(
    *,
    company_name: str,
    website: str = "",
    oblast: str = "",
    address: str = "",
    materials: str = "",
    page_snippet: str = "",
    style_hint: str = "",
    discovery_oblast: str = "",
    construction_project=None,
) -> str:
    from ua_materialy_inquiry_email_uk import (
        inquiry_phone,
        inquiry_sender_name,
    )
    from ua_regional_sender_context import (
        build_regional_sender_instructions_uk,
        resolve_discovery_oblast,
    )
    from ua_regional_construction_refs import (
        build_construction_project_prompt_block_uk,
        pick_construction_project,
    )

    snippet = (page_snippet or "").strip()
    if len(snippet) > 3500:
        snippet = snippet[:3497] + "..."
    style = (style_hint or "професійний, природний B2B-стиль, без шаблонних фраз").strip()
    mats = materials or "будматеріали (загальний асортимент)"
    region_key = resolve_discovery_oblast(
        {"bundesland": oblast, "discovery_bundesland": discovery_oblast},
        fallback=oblast or discovery_oblast,
    )
    project = construction_project or pick_construction_project(
        region_key, seed=company_name or oblast or discovery_oblast
    )
    project_block = build_construction_project_prompt_block_uk(project)
    regional_sender = build_regional_sender_instructions_uk(
        region_key,
        sender_name=inquiry_sender_name(),
        sender_phone=inquiry_phone(),
        construction_project_block=project_block,
    )
    return f"""РОЛЬ
Ти — автор B2B-листів українською. Пишеш УНІКАЛЬНИЙ лист для КОНКРЕТНОЇ фірми-постачальника будматеріалів в Україні.
Кожен лист має відрізнятися формулюваннями — не копіюй один шаблон для всіх.

{regional_sender}

ОДЕРЖУВАЧ (постачальник будматеріалів)
Назва: {company_name}
Сайт: {website or "(немає)"}
Область постачальника: {oblast or "(невідомо)"}
Адреса: {address or "(немає)"}
Категорії матеріалів (з бази): {mats}

ФРАГМЕНТ САЙТУ / ОПИС (використай для персоналізації — згадай їхній асортимент, регіон, спеціалізацію):
{snippet or "(немає — звернися загально до постачальника будматеріалів)"}

ЗАВДАННЯ
Напиши повністю персоналізований лист ЗАПИТУ про співпрацю / оптові ціни / прайс.
• Мова: ВИКЛЮЧНО українська.
• Звернення: «Шановні пані та панове» або персоналізоване до {company_name}.
• Обов'язково згадай щось конкретне про цю фірму-постачальника (асортимент, регіон, тип діяльності).
• Обов'язково згадай обрану регіональну будівельну компанію та об'єкт будівництва з блоку «ОБ'ЄКТ БУДІВНИЦТВА» (з реальною адресою).
• Попроси прайс-лист або контакт відділу опту / продажів.
• Не вигадуй цін, знижок, термінів доставки, яких немає у вхідних даних.
• Стиль: {style}
• Довжина тіла: 140–240 слів (без підпису).

ЗАБОРОНЕНО
• Російська мова
• Німецькі номери (+49, 0049) — заборонено; єдиний контактний телефон: {inquiry_phone()} (у підписі)
• Слова: безкоштовно, акція, терміново, клікніть, знижка 50%
• Один і той самий текст для різних фірм
• Заборонено додавати вкладення / файли / посилання на завантаження
• HTML, markdown
• Представлятися як постачальник або анонімний «покупець» без назви будівельної компанії
• Вигадані або змінені адреси будмайданчика (інша вулиця, номер, місто)

ВИХІД — ЛИШЕ JSON (без markdown):
{{"subject":"...","body":"..."}}

subject: унікальний, до 78 символів, українською; згадай тип об'єкта будівництва або регіон
body: повний лист готовий до відправки (plain text), включно з підписом (ім'я, посада, компанія, tel.)
"""


def build_custom_email_prompt_uk(
    draft: str,
    company_name: str,
    *,
    city_name: str = "",
    delivery_address: str = "",
) -> str:
    ctx_city = f"Регіон: {city_name}. " if city_name else ""
    ctx_addr = f"Адреса доставки (без змін): {delivery_address}. " if delivery_address else ""
    return f"""РОЛЬ
Ти редактор B2B-листів українською. Мінімально адаптуй шаблон під конкретну фірму.

ОДЕРЖУВАЧ
{company_name}
{ctx_city}{ctx_addr}

ЗАВДАННЯ
Адаптуй шаблон (1–2 речення контексту про фірму). Збережи ВСІ факти: обсяги, адреси, телефони, підпис.

ЗАБОРОНЕНО
• Вигадані ціни
• gratis, акція, терміново
• Зміна підпису

ВИХІД (лише JSON)
{{"subject":"...","body":"..."}}

ШАБЛОН
{draft}
"""
