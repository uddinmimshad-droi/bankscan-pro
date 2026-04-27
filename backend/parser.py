import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from utils import clean_amount, date_to_display, is_header_line, is_probable_noise_line, normalize_spaces, parse_date


DATE_PATTERN = (
    r"(?P<date>"
    r"\d{2}[/-]\d{2}[/-]\d{4}|"
    r"\d{2}[/-]\d{2}[/-]\d{2}|"
    r"\d{2}\.\d{2}\.\d{4}|"
    r"\d{2}\.\d{2}\.\d{2}|"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|"
    r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"
    r")"
)
AMOUNT_PATTERN = r"(?:\u20b9|\$|Rs\.?|INR|USD)?\s*-?\(?\d[\d,]*(?:\.\d{1,2})?\)?\s*(?:Cr|Dr|CR|DR)?"


@dataclass
class Transaction:
    transaction_date: datetime
    particulars: str
    withdraw: Optional[Decimal]
    deposit: Optional[Decimal]
    balance: Optional[Decimal]
    source_page: int
    anomalies: List[str] = field(default_factory=list)
    classification_source: str = "unknown"
    pending_amount: Optional[Decimal] = None
    previous_balance_hint: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "transaction_date": date_to_display(self.transaction_date),
            "particulars": self.particulars,
            "withdraw": float(self.withdraw) if self.withdraw is not None else None,
            "deposit": float(self.deposit) if self.deposit is not None else None,
            "balance": float(self.balance) if self.balance is not None else None,
            "source_page": self.source_page,
            "anomalies": self.anomalies,
        }


def parse_transactions(page_payloads: Iterable[Tuple]) -> Tuple[List[Transaction], List[str]]:
    warnings: List[str] = []
    candidates: List[Transaction] = []
    pending: Optional[Transaction] = None
    pending_prefix_lines: List[str] = []
    last_known_balance: Optional[Decimal] = None

    for payload in page_payloads:
        page_number = payload[0]
        text = payload[1] if len(payload) > 1 else ""
        tables = payload[2] if len(payload) > 2 else []

        table_transactions = _parse_page_tables(page_number, tables, warnings)
        if table_transactions:
            if pending:
                candidates.append(pending)
                pending = None
            candidates.extend(table_transactions)
            continue

        for raw_line in (text or "").splitlines():
            line = normalize_spaces(raw_line)
            has_date = re.search(DATE_PATTERN, line) is not None
            if not line or ((is_header_line(line) or is_probable_noise_line(line)) and not has_date):
                continue
            carried_balance = _extract_forward_balance(line)
            if carried_balance is not None:
                if pending:
                    candidates.append(pending)
                    last_known_balance = pending.balance or last_known_balance
                    pending = None
                last_known_balance = carried_balance
                pending_prefix_lines = []
                continue

            parsed = _parse_transaction_line(line, page_number)
            if parsed:
                if pending:
                    candidates.append(pending)
                    last_known_balance = pending.balance or last_known_balance
                parsed.previous_balance_hint = last_known_balance
                if pending_prefix_lines:
                    parsed.particulars = normalize_spaces(" ".join(pending_prefix_lines + [parsed.particulars]))
                    pending_prefix_lines = []
                pending = parsed
                continue

            if pending and _looks_like_continuation(line):
                pending.particulars = normalize_spaces(f"{pending.particulars} {line}")
            elif not pending and _looks_like_prefix_detail(line):
                pending_prefix_lines.append(line)

    if pending:
        candidates.append(pending)

    _classify_by_balance_math(candidates, warnings)
    transactions = _dedupe(candidates, warnings)
    _repair_swapped_amounts(transactions, warnings)
    _validate_order(transactions, warnings)
    _validate_balance_math(transactions, warnings)
    return transactions, warnings


def _parse_page_tables(page_number: int, tables: List[List[List[str]]], warnings: List[str]) -> List[Transaction]:
    transactions: List[Transaction] = []
    pending: Optional[Transaction] = None

    for table in tables or []:
        header_map = None
        for row in table or []:
            cells = [normalize_spaces(cell or "") for cell in row]
            if not any(cells):
                continue

            detected = _detect_table_header(cells)
            if detected:
                header_map = detected
                continue
            if not header_map:
                continue

            parsed = _parse_table_row(page_number, cells, header_map)
            if parsed:
                if pending:
                    transactions.append(pending)
                pending = parsed
                continue

            continuation = normalize_spaces(" ".join(cell for cell in cells if cell))
            if pending and continuation and not is_header_line(continuation) and not is_probable_noise_line(continuation):
                pending.particulars = normalize_spaces(f"{pending.particulars} {continuation}")

    if pending:
        transactions.append(pending)
    if transactions:
        warnings.append(f"Page {page_number}: parsed using table columns to protect debit/credit placement.")
    return transactions


def _detect_table_header(cells: List[str]) -> Optional[Dict[str, int]]:
    mapping: Dict[str, int] = {}
    for index, cell in enumerate(cell.lower() for cell in cells):
        if "date" in cell and "value" not in cell and "date" not in mapping:
            mapping["date"] = index
        if any(token in cell for token in ("particular", "description", "narration", "details", "remarks")):
            mapping["particulars"] = index
        if any(token in cell for token in ("withdraw", "debit", "dr")):
            mapping["withdraw"] = index
        if any(token in cell for token in ("deposit", "credit", "cr")):
            mapping["deposit"] = index
        if "balance" in cell:
            mapping["balance"] = index
    if {"date", "particulars", "balance"}.issubset(mapping) and ("withdraw" in mapping or "deposit" in mapping):
        return mapping
    return None


def _parse_table_row(page_number: int, cells: List[str], header_map: Dict[str, int]) -> Optional[Transaction]:
    def cell(name: str) -> str:
        index = header_map.get(name)
        return cells[index] if index is not None and index < len(cells) else ""

    tx_date = parse_date(cell("date"))
    if not tx_date:
        return None

    withdraw = _non_zero_amount(cell("withdraw")) if "withdraw" in header_map else None
    deposit = _non_zero_amount(cell("deposit")) if "deposit" in header_map else None
    balance = clean_amount(cell("balance"))
    particulars = normalize_spaces(cell("particulars")) or "UNKNOWN PARTICULARS"

    if withdraw is None and deposit is None:
        return None

    anomalies: List[str] = []
    if withdraw is not None and deposit is not None and withdraw > 0 and deposit > 0:
        anomalies.append("Both debit and credit columns contain values in the source table.")

    return Transaction(tx_date, particulars, withdraw, deposit, balance, page_number, anomalies, "table-column")


def _parse_transaction_line(line: str, page_number: int) -> Optional[Transaction]:
    date_match = re.search(DATE_PATTERN, line)
    if not date_match:
        return None
    tx_date = parse_date(date_match.group("date"))
    if not tx_date:
        return None

    after_date = normalize_spaces(line[date_match.end():])
    value_date_match = re.match(DATE_PATTERN, after_date)
    if value_date_match:
        after_date = normalize_spaces(after_date[value_date_match.end():])
    amount_matches = list(re.finditer(AMOUNT_PATTERN, after_date))
    paired = []
    for match in amount_matches:
        amount = clean_amount(match.group(0))
        if amount is not None:
            paired.append((match, match.group(0), amount))
    if len(paired) < 2:
        return None

    balance = paired[-1][2]
    withdraw = None
    deposit = None
    source = "balance-math-pending"
    pending_amount = None

    if len(paired) >= 3:
        debit_match, _, debit_amount = paired[-3]
        credit_match, _, credit_amount = paired[-2]
        if debit_amount > 0 and credit_amount == 0:
            withdraw = debit_amount
            source = "text-debit-credit-columns"
            movement_start = debit_match.start()
        elif credit_amount > 0 and debit_amount == 0:
            deposit = credit_amount
            source = "text-debit-credit-columns"
            movement_start = debit_match.start()
        elif debit_amount == 0 and credit_amount == 0:
            movement_start = debit_match.start()
        else:
            movement_start = paired[-2][0].start()
            pending_amount = paired[-2][2]
            withdraw, deposit, source = _classify_explicit_marker(paired[-2][1], pending_amount)
    else:
        movement_match, movement_text, pending_amount = paired[-2]
        movement_start = movement_match.start()
        withdraw, deposit, source = _classify_explicit_marker(movement_text, pending_amount)

    particulars = normalize_spaces(after_date[:movement_start])
    anomalies: List[str] = []
    if not particulars:
        particulars = "UNKNOWN PARTICULARS"
        anomalies.append("Particulars were empty in source row.")

    return Transaction(tx_date, particulars, withdraw, deposit, balance, page_number, anomalies, source, pending_amount)


def _non_zero_amount(value: str) -> Optional[Decimal]:
    amount = clean_amount(value)
    if amount is None or amount == 0:
        return None
    return amount


def _classify_explicit_marker(movement_text: str, movement: Decimal) -> Tuple[Optional[Decimal], Optional[Decimal], str]:
    lower_amount = movement_text.lower()
    if re.search(r"\bcr\b", lower_amount):
        return None, movement, "explicit-credit-marker"
    if re.search(r"\bdr\b", lower_amount):
        return movement, None, "explicit-debit-marker"
    return None, None, "balance-math-pending"


def _classify_by_balance_math(transactions: List[Transaction], warnings: List[str]) -> None:
    for index, current in enumerate(transactions):
        if current.classification_source != "balance-math-pending":
            continue
        previous_balance = current.previous_balance_hint
        if previous_balance is None and index > 0:
            previous_balance = transactions[index - 1].balance
        movement = current.pending_amount
        if movement is None or previous_balance is None or current.balance is None:
            current.anomalies.append("Debit/credit side could not be proven from balance math.")
            continue
        delta = current.balance - previous_balance
        if abs(delta - movement) <= Decimal("1.00"):
            current.deposit = movement
            current.withdraw = None
            current.classification_source = "balance-math-credit"
        elif abs(delta + movement) <= Decimal("1.00"):
            current.withdraw = movement
            current.deposit = None
            current.classification_source = "balance-math-debit"
        else:
            current.anomalies.append("Debit/credit side could not be matched to running balance.")
            warnings.append(f"Could not prove debit/credit side on {date_to_display(current.transaction_date)} page {current.source_page}.")

    if transactions and transactions[0].classification_source == "balance-math-pending":
        first = transactions[0]
        first.anomalies.append("First row has no previous balance; debit/credit side needs source review.")
        warnings.append(f"First transaction on page {first.source_page} has no previous balance for debit/credit proof.")


def _repair_swapped_amounts(transactions: List[Transaction], warnings: List[str]) -> None:
    for previous, current in zip(transactions, transactions[1:]):
        if previous.balance is None or current.balance is None:
            continue
        expected = previous.balance
        if current.deposit is not None:
            expected += current.deposit
        if current.withdraw is not None:
            expected -= current.withdraw
        if abs(expected - current.balance) <= Decimal("1.00"):
            continue

        swapped = previous.balance
        if current.deposit is not None:
            swapped -= current.deposit
        if current.withdraw is not None:
            swapped += current.withdraw
        if abs(swapped - current.balance) <= Decimal("1.00"):
            current.withdraw, current.deposit = current.deposit, current.withdraw
            current.classification_source = "auto-repaired-by-balance"
            current.anomalies.append("Debit/credit side auto-corrected using running balance.")
            warnings.append(f"Auto-corrected debit/credit side on {date_to_display(current.transaction_date)} page {current.source_page}.")


def _looks_like_continuation(line: str) -> bool:
    if re.search(DATE_PATTERN, line):
        return False
    if is_header_line(line) or is_probable_noise_line(line):
        return False
    return len(line) > 2


def _looks_like_prefix_detail(line: str) -> bool:
    if re.search(DATE_PATTERN, line):
        return False
    if _extract_forward_balance(line) is not None:
        return False
    if is_header_line(line) or is_probable_noise_line(line):
        return False
    if re.search(r"(?i)\b(statement|summary|dr\.?\s*count|cr\.?\s*count|about:blank)\b", line):
        return False
    return len(line) > 2


def _extract_forward_balance(line: str) -> Optional[Decimal]:
    if not re.search(r"(?i)\b(brought|carried)\s+forward\b", line):
        return None
    amounts = [clean_amount(match.group(0)) for match in re.finditer(AMOUNT_PATTERN, line)]
    amounts = [amount for amount in amounts if amount is not None]
    return amounts[-1] if amounts else None


def _dedupe(transactions: List[Transaction], warnings: List[str]) -> List[Transaction]:
    seen = set()
    unique: List[Transaction] = []
    for tx in transactions:
        key = (
            tx.transaction_date.date().isoformat(),
            tx.particulars.lower(),
            str(tx.withdraw),
            str(tx.deposit),
            str(tx.balance),
        )
        if key in seen:
            warnings.append(f"Duplicate transaction skipped from page {tx.source_page}: {tx.particulars}")
            continue
        seen.add(key)
        unique.append(tx)
    return unique


def _validate_order(transactions: List[Transaction], warnings: List[str]) -> None:
    for previous, current in zip(transactions, transactions[1:]):
        delta_days = (current.transaction_date - previous.transaction_date).days
        if delta_days < -7:
            msg = "Transaction date order anomaly near "
            msg += f"{date_to_display(previous.transaction_date)} -> {date_to_display(current.transaction_date)}"
            warnings.append(msg)
            current.anomalies.append("Date appears out of chronological order.")


def _validate_balance_math(transactions: List[Transaction], warnings: List[str]) -> None:
    for previous, current in zip(transactions, transactions[1:]):
        if previous.balance is None or current.balance is None:
            continue
        expected = previous.balance
        if current.deposit is not None:
            expected += current.deposit
        if current.withdraw is not None:
            expected -= current.withdraw
        if abs(expected - current.balance) > Decimal("1.00"):
            current.anomalies.append("Balance does not match debit/credit math.")
            warnings.append(f"Balance anomaly on {date_to_display(current.transaction_date)} page {current.source_page}.")
