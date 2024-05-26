from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class ParsedDependencies:
    all_modules: set[str]
    dependencies: dict[str, set[str]]
