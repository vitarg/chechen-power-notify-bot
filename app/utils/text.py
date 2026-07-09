from __future__ import annotations

import hashlib
import re
import unicodedata

SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s\-.]", re.UNICODE)


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    text = text.lower()
    text = re.sub(r"\bгород\b", "г", text)
    text = re.sub(r"\bгор\.", "г.", text)
    text = re.sub(r"\bг\s*\.", "г.", text)
    text = re.sub(r"\bсело\b", "с", text)
    text = re.sub(r"\bс\s*\.", "с.", text)
    text = re.sub(r"\bпоселок\b", "пос", text)
    text = re.sub(r"\bпос\s*\.", "пос.", text)
    text = re.sub(r"\bулица\b", "ул", text)
    text = re.sub(r"\bул\s*\.", "ул.", text)
    text = re.sub(r"\bпереулок\b", "пер", text)
    text = re.sub(r"\bпер\s*\.", "пер.", text)
    text = PUNCT_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text)
    return text.strip(" .;:-")


def comparable_name(value: str | None) -> str | None:
    if not value:
        return None
    text = normalize_text(value)
    text = re.sub(r"^(г|с|пос|п|ул|пер|пр|б-р|мкр)\.\s*", "", text)
    text = re.sub(r"\bрайон\b", "", text)
    text = SPACE_RE.sub(" ", text)
    return text.strip(" .;:-") or None


def stable_hash(*parts: str) -> str:
    payload = "\n".join(normalize_text(part) for part in parts if part is not None)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def split_csv_like(value: str) -> list[str]:
    pieces = re.split(r"[,;]\s*", value)
    return [piece.strip(" .;:-") for piece in pieces if piece.strip(" .;:-")]
