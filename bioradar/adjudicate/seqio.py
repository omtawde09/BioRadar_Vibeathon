"""Read FASTA/FASTQ (plain or gzip) by CONTENT, never by file name.

The format is decided from the first byte of the data ('>' = FASTA, '@' = FASTQ),
so a file called `sample1.txt` that holds FASTQ still works, and a file called
`mock_community.fastq` that holds FASTA is not misread. Originals are only ever
opened for reading.
"""

from __future__ import annotations

import gzip
from typing import Dict, Iterator, List, NamedTuple, Optional

_COMP = str.maketrans("ACGTRYKMBDHVNacgtrykmbdhvn", "TGCAYRMKVHDBNtgcayrmkvhdbn")


class Record(NamedTuple):
    id: str
    seq: str
    qual: Optional[str]  # None for FASTA


def revcomp(seq: str) -> str:
    return seq.translate(_COMP)[::-1]


def _open(path):
    path = str(path)
    with open(path, "rb") as probe:
        magic = probe.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rt", errors="replace")
    return open(path, "rt", errors="replace")


def detect_format(path) -> str:
    with _open(path) as handle:
        first = handle.read(1)
    if first == ">":
        return "fasta"
    if first == "@":
        return "fastq"
    raise ValueError("not FASTA or FASTQ (first character {!r})".format(first))


def read_records(path, limit: Optional[int] = None) -> Iterator[Record]:
    fmt = detect_format(path)
    with _open(path) as handle:
        count = 0
        if fmt == "fastq":
            while True:
                header = handle.readline()
                if not header:
                    return
                seq = handle.readline().strip()
                handle.readline()
                qual = handle.readline().strip()
                yield Record(header[1:].split()[0] if len(header) > 1 else "", seq.upper(), qual)
                count += 1
                if limit and count >= limit:
                    return
        else:
            name, chunks = None, []  # type: ignore[var-annotated]
            for line in handle:
                line = line.strip()
                if line.startswith(">"):
                    if name is not None:
                        yield Record(name, "".join(chunks).upper(), None)
                        count += 1
                        if limit and count >= limit:
                            return
                    name, chunks = line[1:].split()[0] if len(line) > 1 else "", []
                elif line:
                    chunks.append(line)
            if name is not None:
                yield Record(name, "".join(chunks).upper(), None)


def phred_mean(qual: str, offset: int = 33) -> float:
    if not qual:
        return 0.0
    return sum(ord(c) - offset for c in qual) / len(qual)


class Distinct:
    """A distinct sequence with its read count (what DADA2 calls an ASV, roughly)."""

    __slots__ = ("seq", "count", "first_id", "qual_sum")

    def __init__(self, seq: str, first_id: str) -> None:
        self.seq = seq
        self.count = 0
        self.first_id = first_id
        self.qual_sum = 0.0


def dereplicate(path, limit: Optional[int] = None):
    """Return (distinct sequences sorted by abundance, total reads, format)."""
    fmt = detect_format(path)
    table: Dict[str, Distinct] = {}
    total = 0
    for rec in read_records(path, limit):
        total += 1
        entry = table.get(rec.seq)
        if entry is None:
            entry = table[rec.seq] = Distinct(rec.seq, rec.id)
        entry.count += 1
        if rec.qual:
            entry.qual_sum += phred_mean(rec.qual)
    ordered: List[Distinct] = sorted(table.values(), key=lambda d: (-d.count, d.seq))
    return ordered, total, fmt
