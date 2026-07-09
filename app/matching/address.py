from __future__ import annotations

import re

from app.domain import AddressConfidence, NormalizedAddress
from app.utils.text import comparable_name, normalize_text

DISTRICT_RE = re.compile(r"(?P<district>[а-яА-ЯёЁ\-\s]+?район)")
LOCALITY_PATTERNS = [
    re.compile(r"(?:^|[\s,;:-])г\.\s*(?P<value>[а-яА-ЯёЁ\-\s]+?)(?=,|;|$|\s+ул\.|\s+пер\.)"),
    re.compile(r"(?:^|[\s,;:-])с\.\s*(?P<value>[а-яА-ЯёЁ\-\s]+?)(?=,|;|$|\s+ул\.|\s+пер\.)"),
    re.compile(r"(?:^|[\s,;:-])пос\.\s*(?P<value>[а-яА-ЯёЁ\-\s]+?)(?=,|;|$|\s+ул\.|\s+пер\.)"),
    re.compile(r"(?:^|[\s,;:-])п\.\s*(?P<value>[а-яА-ЯёЁ\-\s]+?)(?=,|;|$|\s+ул\.|\s+пер\.)"),
]
STREET_RE = re.compile(
    r"(?:^|[\s,;:-])(?:ул\.|пер\.|пр\.|б-р\.?)\s*(?P<street>[а-яА-ЯёЁ0-9.\-\s]+?)(?=,|;|$)"
)


def parse_user_address(raw_text: str) -> NormalizedAddress:
    normalized = normalize_text(raw_text)
    district = _first_group(DISTRICT_RE, raw_text, "district")
    locality = _extract_locality(raw_text)
    street = _first_group(STREET_RE, raw_text, "street")
    if locality is None and district is None and "," in raw_text:
        first_piece = raw_text.split(",", 1)[0].strip()
        if first_piece and "район" not in normalize_text(first_piece):
            locality = first_piece

    if locality and street:
        confidence = AddressConfidence.HIGH
    elif locality:
        confidence = AddressConfidence.MEDIUM
    else:
        # For common one-token inputs like "Урус-Мартан", treat it as locality.
        compact = raw_text.strip(" .;:-")
        if compact and "," not in compact and len(compact.split()) <= 3 and "район" not in normalized:
            locality = compact
            confidence = AddressConfidence.MEDIUM
        else:
            confidence = AddressConfidence.LOW

    landmark = None
    return NormalizedAddress(
        raw_text=raw_text,
        normalized_text=normalized,
        district=comparable_name(district),
        locality=comparable_name(locality),
        street=comparable_name(street),
        landmark=comparable_name(landmark),
        confidence=confidence,
    )


def _first_group(pattern: re.Pattern[str], value: str, group_name: str) -> str | None:
    match = pattern.search(value)
    if not match:
        return None
    return match.group(group_name).strip()


def _extract_locality(value: str) -> str | None:
    for pattern in LOCALITY_PATTERNS:
        match = pattern.search(value)
        if match:
            return match.group("value").strip()
    return None
