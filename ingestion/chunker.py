"""Section-aware chunking.

Default granularity is ONE section (rider / paragraph / clause) per chunk. Any
single section longer than ``max_chars`` is split further into overlapping
sub-chunks so that no chunk exceeds the embedding model's practical input size.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List


@dataclass
class Chunk:
    chunk_id: str
    case_id: str
    case_name: str
    court: str
    jurisdiction: str
    date: str
    case_type: str
    source: str
    section_type: str
    section_number: str
    heading: str
    order: int
    part: int           # 0 when the section was not split
    n_parts: int
    text: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def citation(self) -> str:
        label = {"rider": "Rider", "paragraph": "para.",
                 "clause": "Clause"}[self.section_type]
        num = str(self.section_number).strip()
        if num.lower().startswith(label.rstrip(".").lower()):
            s = f"{self.case_name}, {num.title() if num.isupper() else num}"
        else:
            s = f"{self.case_name}, {label} {num}"
        if self.n_parts > 1:
            s += f" (part {self.part + 1} of {self.n_parts})"
        return s


def _split_long(text: str, max_chars: int, overlap: int) -> List[str]:
    """Split on sentence-ish boundaries, keeping ``overlap`` characters of tail."""
    if len(text) <= max_chars:
        return [text]
    parts: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            window = text[start:end]
            cut = max(window.rfind(". "), window.rfind("; "), window.rfind(") "))
            if cut > max_chars * 0.5:
                end = start + cut + 1
        parts.append(text[start:end].strip())
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return [p for p in parts if p]


def chunk_case(case: Dict[str, Any], max_chars: int = 1800,
               overlap: int = 200) -> List[Chunk]:
    chunks: List[Chunk] = []
    for sec in sorted(case.get("sections", []), key=lambda s: s.get("order", 0)):
        pieces = _split_long(sec["text"], max_chars, overlap)
        n = len(pieces)
        for i, piece in enumerate(pieces):
            suffix = f"-p{i}" if n > 1 else ""
            cid = (f"{case['case_id']}::{sec['section_type']}"
                   f"::{sec['section_number']}{suffix}")
            chunks.append(Chunk(
                chunk_id=cid,
                case_id=case["case_id"],
                case_name=case["case_name"],
                court=case.get("court", ""),
                jurisdiction=case.get("jurisdiction", ""),
                date=case.get("date", ""),
                case_type=case.get("case_type", ""),
                source=case.get("source", "synthetic"),
                section_type=sec["section_type"],
                section_number=str(sec["section_number"]),
                heading=sec.get("heading", ""),
                order=int(sec.get("order", 0)),
                part=i,
                n_parts=n,
                text=piece,
            ))
    return chunks


def chunk_cases(cases: Iterable[Dict[str, Any]], max_chars: int = 1800,
                overlap: int = 200) -> List[Chunk]:
    out: List[Chunk] = []
    for c in cases:
        out.extend(chunk_case(c, max_chars, overlap))
    return out
