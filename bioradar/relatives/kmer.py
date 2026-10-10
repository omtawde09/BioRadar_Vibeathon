"""Vector embeddings of DNA fragments and nearest-neighbour search over the reference.

Embedding = canonical k-mer TF-IDF vector, L2-normalised:

* canonical k-mers: a k-mer and its reverse complement count as one feature, so a read
  sequenced from either strand embeds to the same vector (no orientation step needed);
* TF-IDF: k-mers present in almost every fish 12S fragment (conserved stem regions) carry
  little signal about WHICH fish, so they are down-weighted by inverse document frequency
  computed over the reference;
* cosine similarity between two vectors is the relatedness score used to rank relatives.

`dense()` folds the sparse vector into a fixed-size dense vector (signed feature hashing,
several hashes per k-mer) for export, plotting or an external vector store. Search itself
uses the exact sparse cosine through an inverted index, so nothing is lost to the projection.

Nothing is trained: the "model" is the reference, its IDF weights and the index.
Standard library only; Python 3.8 compatible.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Sequence, Tuple

K = 6
DENSE_DIMS = 128
DENSE_HASHES = 4
_CODE = {"A": 0, "C": 1, "G": 2, "T": 3}
_MASK = (1 << (2 * K)) - 1

SparseVec = Dict[int, float]


def kmer_codes(seq: str, k: int = K) -> List[int]:
    """Canonical k-mer integer codes. Windows with N or other symbols are skipped."""
    seq = seq.upper()
    mask = (1 << (2 * k)) - 1
    shift = 2 * (k - 1)
    out: List[int] = []
    fwd = rev = 0
    valid = 0
    for ch in seq:
        code = _CODE.get(ch)
        if code is None:
            valid = 0
            fwd = rev = 0
            continue
        fwd = ((fwd << 2) | code) & mask
        rev = (rev >> 2) | ((3 - code) << shift)
        valid += 1
        if valid >= k:
            out.append(fwd if fwd < rev else rev)
    return out


def term_counts(seq: str, k: int = K) -> Counter:
    return Counter(kmer_codes(seq, k))


def normalise(vec: SparseVec) -> SparseVec:
    norm = math.sqrt(sum(v * v for v in vec.values()))
    return {key: v / norm for key, v in vec.items()} if norm else {}


def cosine(a: SparseVec, b: SparseVec) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(key, 0.0) for key, v in a.items())


class Embedder:
    """TF-IDF over canonical k-mers, with IDF learned from a set of reference fragments."""

    def __init__(self, idf: Dict[int, float], n_docs: int, k: int = K) -> None:
        self.idf = idf
        self.n_docs = n_docs
        self.k = k
        self.default_idf = math.log((1 + n_docs) / 1.0) + 1.0  # k-mer never seen in reference

    @classmethod
    def fit(cls, sequences: Iterable[str], k: int = K) -> "Embedder":
        df: Counter = Counter()
        n = 0
        for seq in sequences:
            df.update(set(kmer_codes(seq, k)))
            n += 1
        idf = {code: math.log((1 + n) / (1 + d)) + 1.0 for code, d in df.items()}
        return cls(idf, n, k)

    def embed(self, seq: str) -> SparseVec:
        counts = term_counts(seq, self.k)
        return normalise({c: tf * self.idf.get(c, self.default_idf) for c, tf in counts.items()})


def dense(vec: SparseVec, dims: int = DENSE_DIMS, hashes: int = DENSE_HASHES) -> List[float]:
    """Fixed-size dense embedding by signed feature hashing (deterministic, no training).
    Cosine between dense vectors approximates the sparse cosine."""
    out = [0.0] * dims
    for code, value in vec.items():
        digest = hashlib.blake2b(code.to_bytes(4, "little"), digest_size=2 * hashes).digest()
        for h in range(hashes):
            slot = int.from_bytes(digest[2 * h:2 * h + 2], "little")
            sign = 1.0 if slot & 1 else -1.0
            out[(slot >> 1) % dims] += sign * value / math.sqrt(hashes)
    norm = math.sqrt(sum(x * x for x in out))
    return [round(x / norm, 6) for x in out] if norm else out


class Index:
    """Exact cosine search over embedded reference fragments via an inverted index."""

    def __init__(self, embedder: Embedder, labels: Sequence[Tuple[str, str]],
                 vectors: List[SparseVec]) -> None:
        self.embedder = embedder
        self.labels = list(labels)  # (accession, species) per vector
        self.vectors = vectors
        self.postings: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        for i, vec in enumerate(vectors):
            for code, w in vec.items():
                self.postings[code].append((i, w))

    @classmethod
    def build(cls, entries: Sequence[Tuple[str, str, str]], k: int = K) -> "Index":
        """entries: (accession, species, sequence)."""
        embedder = Embedder.fit((e[2] for e in entries), k)
        vectors = [embedder.embed(e[2]) for e in entries]
        return cls(embedder, [(e[0], e[1]) for e in entries], vectors)

    def scores(self, query: SparseVec) -> Dict[int, float]:
        acc: Dict[int, float] = defaultdict(float)
        for code, w in query.items():
            for i, rw in self.postings.get(code, ()):
                acc[i] += w * rw
        return acc

    def nearest_species(self, seq: str, top: int = 10, exclude_species: Iterable[str] = ()
                        ) -> List[Tuple[str, str, float]]:
        """Best entry per species, most similar first: [(species, accession, cosine)]."""
        excluded = set(exclude_species)
        best: Dict[str, Tuple[float, str]] = {}
        for i, score in self.scores(self.embedder.embed(seq)).items():
            acc_id, species = self.labels[i]
            if species in excluded:
                continue
            if species not in best or score > best[species][0]:
                best[species] = (score, acc_id)
        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:top]
        return [(sp, acc_id, round(score, 4)) for sp, (score, acc_id) in ranked]
