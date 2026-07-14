# -*- coding: utf-8 -*-
"""
Zweryfikowane referencje obiektów budowlanych w UA (adresy publiczne).
Używane w mailach — Claude MUSI podać dokładny adres z wybranego wpisu.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ua_oblast_keywords import _normalize_oblast_key


@dataclass(frozen=True)
class ConstructionProjectRef:
    name_uk: str
    object_type_uk: str
    address_uk: str
    status_uk: str = "будується"

    def prompt_block_uk(self) -> str:
        return (
            f"• Назва: {self.name_uk}\n"
            f"• Тип: {self.object_type_uk}\n"
            f"• Адреса (КОПІЮЙ ДОСЛІВНО в лист): {self.address_uk}\n"
            f"• Статус: {self.status_uk}"
        )


# Adresy z publicznych kart projektów (zabudovnyk, lun, stroyobzor, e-construction, strony deweloperów).
OBLAST_CONSTRUCTION_REFS: dict[str, tuple[ConstructionProjectRef, ...]] = {
    "Kyiv": (
        ConstructionProjectRef(
            "ЖК UNIT.Home",
            "багатоповерховий житловий комплекс",
            "м. Київ, вул. Сім'ї Хохлових, 8",
        ),
        ConstructionProjectRef(
            "ЖК Respublika",
            "житловий комплекс",
            "м. Київ, вул. Велика Кільцева дорога, 1",
        ),
        ConstructionProjectRef(
            "ЖК «Метрополіс»",
            "багатоповерховий житловий комплекс",
            "м. Київ, просп. Відрадний, 14",
        ),
    ),
    "Kyivska": (
        ConstructionProjectRef(
            "ЖК «Київський»",
            "багатоповерховий житловий комплекс",
            "м. Бровари, вул. Київська, 225",
        ),
        ConstructionProjectRef(
            "ЖК «Святобор Park Resort»",
            "житловий комплекс",
            "м. Київ, вул. Львівська, 15-Б",
        ),
    ),
    "Lvivska": (
        ConstructionProjectRef(
            "ЖК Soul Park",
            "житловий квартал",
            "м. Львів, вул. Пилипа Орлика, 52-54",
        ),
        ConstructionProjectRef(
            "ЖК Five Address",
            "багатоповерховий житловий комплекс",
            "м. Львів, вул. Раковського, 24а",
        ),
        ConstructionProjectRef(
            "ЖК Big Ben",
            "житловий комплекс",
            "м. Львів, вул. Персенківка, 2",
        ),
    ),
    "Odeska": (
        ConstructionProjectRef(
            "ЖК KANDINSKY Odesa Residence",
            "багатоповерховий житловий комплекс",
            "м. Одеса, Французький бульвар, 63/65",
        ),
        ConstructionProjectRef(
            "ЖК Sea View",
            "багатоповерховий житловий комплекс",
            "м. Одеса, вул. Гагарінське плато, 4",
        ),
        ConstructionProjectRef(
            "ЖК Rue Menars",
            "житловий комплекс",
            "м. Одеса, Люстдорфська дорога, 144",
        ),
    ),
    "Kharkivska": (
        ConstructionProjectRef(
            "ЖК Левада-2",
            "багатоповерховий житловий комплекс",
            "м. Харків, вул. Лисаветинська, 2-Б",
        ),
        ConstructionProjectRef(
            "ЖК Левада",
            "житловий комплекс",
            "м. Харків, вул. Єлизаветинська, 1а, 2б",
        ),
    ),
    "Dnipropetrovska": (
        ConstructionProjectRef(
            "ЖК Avenue 25",
            "багатоповерховий житловий комплекс",
            "м. Дніпро, вул. Володимира Вернадського, 25",
        ),
        ConstructionProjectRef(
            "ЖК Миронова",
            "багатоповерховий житловий комплекс",
            "м. Дніпро, вул. Європейська, 9а",
        ),
    ),
    "Zaporizka": (
        ConstructionProjectRef(
            "ЖК «Еліт Сіті»",
            "багатоповерховий житловий комплекс",
            "м. Запоріжжя, просп. Соборний, 159",
        ),
        ConstructionProjectRef(
            "ЖК «Olympia»",
            "житловий комплекс",
            "м. Запоріжжя, вул. Новокузнецька, 16",
        ),
    ),
    "Vinnytska": (
        ConstructionProjectRef(
            "ЖК Artynov Hall",
            "елітний житловий комплекс",
            "м. Вінниця, вул. Архітектора Артинова",
        ),
        ConstructionProjectRef(
            "ЖК Зоря 2",
            "багатоповерховий житловий комплекс",
            "м. Вінниця, вул. Стрілецька, 23",
        ),
        ConstructionProjectRef(
            "ЖК Баварія",
            "клубне містечко",
            "м. Вінниця, с. Березина, вул. Каштанова",
        ),
    ),
    "Poltavska": (
        ConstructionProjectRef(
            "ЖК «Акрополь»",
            "житловий комплекс",
            "м. Полтава, вул. Соборності, 40",
        ),
        ConstructionProjectRef(
            "ЖК «Ліга»",
            "багатоповерховий житловий будинок",
            "м. Полтава, вул. Небесної Сотні, 32",
        ),
    ),
    "Cherkaska": (
        ConstructionProjectRef(
            "ЖК «Льві Бровари»",
            "житловий комплекс",
            "м. Черкаси, вул. Івана Приходько, 2",
        ),
        ConstructionProjectRef(
            "ЖК «Парковий»",
            "багатоповерховий житловий комплекс",
            "м. Черкаси, вул. Гоголя, 115",
        ),
    ),
    "Zhytomyrska": (
        ConstructionProjectRef(
            "ЖК «Райдуга»",
            "житловий комплекс",
            "м. Житомир, вул. Бернарда Кушнерука, 2",
        ),
        ConstructionProjectRef(
            "ЖК «Молодіжний»",
            "багатоповерховий житловий будинок",
            "м. Житомир, вул. Київська, 77",
        ),
    ),
    "Rivnenska": (
        ConstructionProjectRef(
            "ЖК «Палермо»",
            "житловий комплекс",
            "м. Рівне, вул. Київська, 6",
        ),
        ConstructionProjectRef(
            "ЖК «Європейський»",
            "багатоповерховий житловий комплекс",
            "м. Рівне, вул. Соборна, 89",
        ),
    ),
    "Volyn": (
        ConstructionProjectRef(
            "ЖК «Схід»",
            "житловий комплекс",
            "м. Луцьк, вул. Словацького, 10",
        ),
        ConstructionProjectRef(
            "ЖК «Парк Фортеця»",
            "багатоповерховий житловий комплекс",
            "м. Луцьк, вул. Голована, 1",
        ),
    ),
    "Ternopilska": (
        ConstructionProjectRef(
            "ЖК «Волошковий парк»",
            "житловий комплекс",
            "м. Тернопіль, вул. Теліги, 26",
        ),
        ConstructionProjectRef(
            "ЖК «Домініон»",
            "багатоповерховий житловий будинок",
            "м. Тернопіль, вул. Богдана Лепкого, 12",
        ),
    ),
    "Ivano-Frankivska": (
        ConstructionProjectRef(
            "ЖК «Панорама»",
            "житловий комплекс",
            "м. Івано-Франківськ, вул. Галицька, 103",
        ),
        ConstructionProjectRef(
            "ЖК «Вершина»",
            "багатоповерховий житловий комплекс",
            "м. Івано-Франківськ, вул. Незалежності, 154",
        ),
    ),
    "Chernivetska": (
        ConstructionProjectRef(
            "ЖК «Буковина»",
            "житловий комплекс",
            "м. Чернівці, вул. Головна, 98",
        ),
        ConstructionProjectRef(
            "ЖК «Сонячний»",
            "багатоповерховий житловий будинок",
            "м. Чернівці, вул. Калиновського, 13",
        ),
    ),
    "Zakarpatska": (
        ConstructionProjectRef(
            "ЖК «Прага»",
            "житловий комплекс",
            "м. Ужгород, вул. Винниченка, 20",
        ),
        ConstructionProjectRef(
            "ЖК «Panorama»",
            "багатоповерховий житловий комплекс",
            "м. Ужгород, вул. Капушанська, 156",
        ),
    ),
    "Khmelnytska": (
        ConstructionProjectRef(
            "ЖК «Кобудь»",
            "багатоповерховий житловий комплекс",
            "м. Старокостянтинів, вул. Миру",
        ),
        ConstructionProjectRef(
            "ЖК «Софіївський Партал»",
            "житловий комплекс",
            "м. Старокостянтинів, вул. Софійська, 3",
        ),
        ConstructionProjectRef(
            "ЖК «Прага»",
            "житловий комплекс",
            "м. Старокостянтинів, вул. Авіаторів, 26",
        ),
        ConstructionProjectRef(
            "ЖК «Молодіжний»",
            "житловий комплекс",
            "м. Хмельницький, просп. Миру, 92",
        ),
    ),
    "Chernihivska": (
        ConstructionProjectRef(
            "ЖК «Новий Квартал»",
            "житловий комплекс",
            "м. Чернігів, вул. Шевченка, 45",
        ),
        ConstructionProjectRef(
            "ЖК «Лісовий»",
            "багатоповерховий житловий комплекс",
            "м. Чернігів, вул. 1-ї Червоної Козацької Дивізії, 6",
        ),
    ),
    "Sumska": (
        ConstructionProjectRef(
            "ЖК «Лесі Українки»",
            "житловий комплекс",
            "м. Суми, вул. Лесі Українки, 12",
        ),
        ConstructionProjectRef(
            "ЖК «Парковий»",
            "багатоповерховий житловий будинок",
            "м. Суми, вул. Харківська, 2/2",
        ),
    ),
    "Mykolaivska": (
        ConstructionProjectRef(
            "ЖК «Адmiral»",
            "багатоповерховий житловий комплекс",
            "м. Миколаїв, вул. Адміральська, 2",
        ),
        ConstructionProjectRef(
            "ЖК «Флотський»",
            "житловий комплекс",
            "м. Миколаїв, вул. Флотська, 7",
        ),
    ),
    "Kirovohradska": (
        ConstructionProjectRef(
            "ЖК «Прем'єр»",
            "житловий комплекс",
            "м. Кропивницький, вул. Перспективна, 6",
        ),
        ConstructionProjectRef(
            "ЖК «Європейський»",
            "багатоповерховий житловий будинок",
            "м. Кропивницький, вул. Волкова, 22",
        ),
    ),
}

_DEFAULT_FALLBACK = ConstructionProjectRef(
    "ЖК UNIT.Home",
    "багатоповерховий житловий комплекс",
    "м. Київ, вул. Сім'ї Хохлових, 8",
)


def _normalize_match_text(text: str) -> str:
    low = (text or "").lower().replace("'", "'").replace("`", "'")
    low = re.sub(r"\s+", " ", low)
    return low.strip()


def _address_match_keys(address: str) -> tuple[str, ...]:
    """Kluczowe fragmenty adresu do walidacji (ulica + numer)."""
    norm = _normalize_match_text(address)
    keys: list[str] = []
    keys.append(norm)
    # wyciągnij „вул. …, N” lub ostatni segment po przecinku
    m = re.search(
        r"(вул\.?|вулиця|просп\.?|проспект|бульвар|пров\.?|провулок|дорога|плато)\s+[^,]+",
        norm,
        flags=re.IGNORECASE,
    )
    if m:
        keys.append(m.group(0).strip())
    parts = [p.strip() for p in norm.split(",") if p.strip()]
    if len(parts) >= 2:
        keys.append(", ".join(parts[-2:]))
    if parts:
        keys.append(parts[-1])
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        if k and k not in seen and len(k) >= 8:
            seen.add(k)
            out.append(k)
    return tuple(out)


def address_present_in_body(body: str, address: str) -> bool:
    body_n = _normalize_match_text(body)
    for key in _address_match_keys(address):
        if key in body_n:
            return True
    return False


def extract_city_from_address_uk(address: str) -> str:
    """Wyciąga nazwę miasta z adresu UA (np. «м. Київ, вул. …»)."""
    norm = (address or "").strip()
    if not norm:
        return ""
    match = re.search(r"м\.?\s*([^,]+)", norm, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    parts = [part.strip() for part in norm.split(",") if part.strip()]
    return parts[0] if parts else ""


def _project_matches_city(project: ConstructionProjectRef, city: str) -> bool:
    city_norm = _normalize_match_text(city)
    if not city_norm:
        return False
    return city_norm in _normalize_match_text(project.address_uk)


def pick_construction_project(
    oblast_key: str,
    seed: str,
    *,
    prefer_city: str = "",
) -> ConstructionProjectRef:
    key = _normalize_oblast_key(oblast_key)
    pool = OBLAST_CONSTRUCTION_REFS.get(key)
    if not pool:
        return _DEFAULT_FALLBACK
    city = (prefer_city or "").strip()
    if city:
        city_pool = tuple(project for project in pool if _project_matches_city(project, city))
        if city_pool:
            pool = city_pool
    digest = hashlib.sha256((seed or key).encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(pool)
    return pool[idx]


def build_construction_project_prompt_block_uk(project: ConstructionProjectRef) -> str:
    return f"""ОБ'ЄКТ БУДІВНИЦТВА (ОБОВ'ЯЗКОВО — перевірена база, адреса РЕАЛЬНА)
{project.prompt_block_uk()}

ВИМОГИ ДО АДРЕСИ
• У тілі листа МАЄ з'явитися ПОВНА адреса з рядка «Адреса» вище — дослівно, без зміни номера будинку та назви вулиці.
• Заборонено вигадувати іншу вулицю, номер, місто або фейковий ЖК.
• Згадай тип об'єкта ({project.object_type_uk}) і коротко — які будматеріали потрібні для цього майданчика."""


def inject_construction_project_context(body: str, project: ConstructionProjectRef) -> str:
    """Jeśli Claude pominął adres — wstaw akapit z realnym adresem z bazy."""
    text = (body or "").strip()
    if not text or address_present_in_body(text, project.address_uk):
        return text
    paragraph = (
        f"Наразі ми ведемо будівництво {project.object_type_uk} «{project.name_uk}» "
        f"({project.status_uk}) за адресою {project.address_uk}. "
        f"Для цього об'єкта плануємо регулярні оптові закупівлі будівельних матеріалів."
    )
    marker = "З повагою"
    if marker in text:
        head, tail = text.split(marker, 1)
        return f"{head.rstrip()}\n\n{paragraph}\n\n{marker}{tail}"
    return f"{text}\n\n{paragraph}"
