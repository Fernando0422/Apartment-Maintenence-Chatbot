from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceSpec:
    name: str
    source_type: str
    enabled: bool
    modes: tuple[str, ...]
    config: dict[str, Any]


class ListingSourceConnector(ABC):
    def __init__(self, spec: SourceSpec) -> None:
        self.spec = spec

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Return raw listing payloads in unified dict format."""
        raise NotImplementedError
