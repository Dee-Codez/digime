import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Memory:
    source: str
    title: str
    text: str
    url: str = ""
    ts: str = ""
    metadata: dict = field(default_factory=dict)

    def id(self) -> str:
        key = f"{self.source}|{self.ts}|{self.url}|{self.title}|{self.text}"
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
        return f"{self.source}:{digest}"

    def to_dict(self) -> dict:
        return asdict(self)
