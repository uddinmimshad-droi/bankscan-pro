import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


DATE_FORMATS = (
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%d.%m.%Y",
    "%d.%m.%y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d %Y",
    "%B %d %Y",
)


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def parse_date(value: str) -> Optional[datetime]:
    value = normalize_spaces(value).replace(",", "")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def date_to_display(value: Optional[datetime]) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def clean_amount(value: str) -> Optional[Decimal]:
    if value is None:
        return None
    cleaned = str(value)
    cleaned = re.sub(r"(?i)\b(cr|dr)\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(rs\.?|inr|usd)\b", "", cleaned)
    cleaned = cleaned.replace("₹", "").replace("$", "").replace(",", "")
    cleaned = cleaned.replace("(", "-").replace(")", "")
    cleaned = cleaned.strip()
    if not cleaned or cleaned in {"-", "."}:
        return None
    match = re.search(r"-?\d+(?:\.\d{1,2})?", cleaned)
    if not match:
        return None
    try:
        return Decimal(match.group(0)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    return float(value) if value is not None else None


def looks_like_garbage_text(text: str) -> bool:
    text = text or ""
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 40:
        return True
    readable = sum(ch.isalnum() for ch in compact)
    return readable / max(len(compact), 1) < 0.45


def is_probable_noise_line(line: str) -> bool:
    line = normalize_spaces(line).lower()
    if not line:
        return True
    noise_patterns = (
        r"^page\s+\d+",
        r"^\d+\s+of\s+\d+$",
        r"statement\s+of\s+account",
        r"computer\s+generated",
        r"this\s+is\s+a\s+system\s+generated",
        r"branch\s+address",
        r"ifsc",
        r"micr",
        r"customer\s+id",
        r"account\s+number",
        r"opening\s+balance",
        r"closing\s+balance",
    )
    return any(re.search(pattern, line) for pattern in noise_patterns)


def is_header_line(line: str) -> bool:
    line = normalize_spaces(line).lower()
    if not line:
        return True
    header_hits = sum(
        token in line
        for token in (
            "date",
            "particular",
            "description",
            "narration",
            "withdraw",
            "debit",
            "deposit",
            "credit",
            "balance",
        )
    )
    return header_hits >= 3
