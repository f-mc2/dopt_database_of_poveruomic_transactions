from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Period:
    label: str
    start_date: str
    end_date: str


@dataclass(frozen=True)
class Group:
    label: str
    payers: List[str]
    payees: List[str]
    include_missing_payer: bool = False
    include_missing_payee: bool = False


@dataclass(frozen=True)
class Node:
    label: str
    kind: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tag: Optional[str] = None
