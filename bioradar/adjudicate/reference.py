"""The reference list and the nearest-match search (pure Python, no BLAST).

The reference is the MiFish-U amplicon region cut out of every RefSeq fish
mitochondrial genome, built by `build_reference()` from files `fetch` downloaded.
Nothing is trained: a query is compared with reference sequences directly, first
by shared k-mers to shortlist candidates, then by identity along the best
alignment. Identity is simply (bases that match) / (query length).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from bioradar.adjudicate.seqio import read_records, revcomp

REPO_ROOT = Path(__file__).resolve().parents[2]
REF_DIR = REPO_ROOT / "data" / "real_challenge" / "reference_12s"
CACHE_DIR = REPO_ROOT / "data" / "real_challenge" / "cache"

# MiFish-U primers (Miya et al. 2015). The reads in the chosen dataset contain
# them, so the reference amplicon is cut from primer start to primer end.
PRIMER_F = "GTCGGTAAAACTCGTGCCAGC"
PRIMER_R = "CATAGTGGGGTATCTAATCCCAGTTTG"
PRIMER_R_RC = revcomp(PRIMER_R)
AMPLICON_MIN, AMPLICON_MAX = 120, 260
SEARCH_WINDOW = 3000  # 12S sits in the first few kb of a fish mitogenome
MAX_PRIMER_MISMATCH = 5

K = 11
POSTING_CAP = 150  # k-mers shared by more references than this carry no signal


class Match(NamedTuple):
    species: str
    accession: str
    identity: float
    strand: str


def _hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def _find_primer(seq: str, primer: str) -> List[int]:
    """Start positions where `primer` matches with few mismatches (seeded scan)."""
    hits = []
    n = len(primer)
    seeds = [(0, primer[:8]), (7, primer[7:15]), (n - 8, primer[n - 8:])]
    seen = set()
    for offset, seed in seeds:
        start = 0
        while True:
            i = seq.find(seed, start)
            if i < 0:
                break
            pos = i - offset
            if pos >= 0 and pos not in seen and pos + n <= len(seq):
                seen.add(pos)
                if _hamming(seq[pos:pos + n], primer) <= MAX_PRIMER_MISMATCH:
                    hits.append(pos)
            start = i + 1
    return sorted(hits)


def extract_amplicon(genome: str) -> Optional[str]:
    """Cut the primer-to-primer region out of a mitogenome (either strand)."""
    for strand in (genome, revcomp(genome)):
        window = strand[:SEARCH_WINDOW]
        for f in _find_primer(window, PRIMER_F):
            for r in _find_primer(window, PRIMER_R_RC):
                length = r + len(PRIMER_R_RC) - f
                if AMPLICON_MIN <= length <= AMPLICON_MAX:
                    return window[f:r + len(PRIMER_R_RC)]
    return None


_BINOMIAL = re.compile(r"^[A-Z][a-z]+ [a-z][a-z-]+$")


def is_resolved_species(name: str) -> bool:
    """'Oreochromis sp.' or 'Genus cf. species' is not a species-level reference."""
    return bool(_BINOMIAL.match(name)) and name.split()[1] not in {"sp", "cf", "aff", "gen"}


def _species_from_header(header: str) -> Tuple[str, str]:
    words = header.split()
    accession = words[0]
    name = []
    for w in words[1:]:
        if w.lower().startswith("mitochondri"):
            break
        name.append(w)
    return accession, " ".join(name[:2]) if len(name) >= 2 else " ".join(name)


def _fasta_with_headers(path: Path):
    """(full header line, sequence) pairs -- seqio keeps only the first token."""
    header, chunks = None, []  # type: ignore[var-annotated]
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks).upper()
                header, chunks = line[1:], []
            elif line:
                chunks.append(line)
    if header is not None:
        yield header, "".join(chunks).upper()


def build() -> Dict[str, Any]:
    """Build data/real_challenge/reference_12s/ from the downloaded RefSeq FASTA."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    total = unresolved = 0
    rows = []
    for header, genome in _fasta_with_headers(CACHE_DIR / "refseq_fish_mito.fasta"):
        total += 1
        amp = extract_amplicon(genome)
        if amp:
            acc, species = _species_from_header(header)
            if is_resolved_species(species):
                rows.append((acc, species, amp))
            else:
                unresolved += 1
    result = _write_reference(rows, total, len(rows))
    result["excluded_unresolved_names"] = unresolved
    meta_file = REF_DIR / "reference.json"
    meta_doc = json.loads(meta_file.read_text(encoding="utf-8"))
    meta_doc["excluded_unresolved_names"] = unresolved
    meta_doc["excluded_note"] = ("Mitogenomes named only to genus ('Genus sp.', 'cf.', 'aff.') "
                                 "are not species-level references and are left out.")
    meta_file.write_text(json.dumps(meta_doc, indent=2), encoding="utf-8")
    human = list(_fasta_with_headers(CACHE_DIR / "human_mito.fasta"))
    if human:
        amp = extract_amplicon(human[0][1])
        if amp:
            (REF_DIR / "human_contaminant.fasta").write_text(
                ">{} Homo sapiens MiFish-U amplicon\n{}\n".format(human[0][0].split()[0], amp),
                encoding="utf-8")
            result["human_contaminant_amplicon_bp"] = len(amp)
            meta_path = REF_DIR / "reference.json"
            result_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            result_meta["human_contaminant_amplicon_bp"] = len(amp)
            meta_path.write_text(json.dumps(result_meta, indent=2), encoding="utf-8")
    return result


def _write_reference(rows, total: int, kept: int) -> Dict[str, Any]:
    fasta = REF_DIR / "reference.fasta"
    with fasta.open("w", encoding="utf-8") as out:
        for acc, species, amp in rows:
            out.write(">{}|{}\n{}\n".format(acc, species.replace(" ", "_"), amp))
    fetch_meta = {}
    fm = CACHE_DIR / "refseq_fetch.json"
    if fm.is_file():
        fetch_meta = json.loads(fm.read_text(encoding="utf-8"))
    species = sorted({s for _, s, _ in rows})
    meta = {
        "name": "RefSeq fish mitogenomes, MiFish-U amplicon",
        "reference_database_version": "NCBI RefSeq, retrieved {}".format(
            fetch_meta.get("retrieved_at", "unknown")),
        "ncbi_query": fetch_meta.get("query", ""),
        "mitogenomes_downloaded": total,
        "amplicons_extracted": kept,
        "distinct_species": len(species),
        "primers": {"forward": PRIMER_F, "reverse": PRIMER_R},
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Amplicon = primer-to-primer region cut from each mitogenome with up to "
                "{} primer mismatches. Mitogenomes without a findable amplicon are not "
                "in the list, so some fish are genuinely absent from this reference.".format(
                    MAX_PRIMER_MISMATCH),
    }
    (REF_DIR / "reference.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------


def _banded_identity(query: str, ref: str, diag: int, band: int = 5) -> float:
    """Edit-distance identity of `query` against ref, free reference ends, banded."""
    n, m = len(query), len(ref)
    INF = 10 ** 6
    prev = {}
    for j in range(max(0, diag - band), min(m, diag + band) + 1):
        prev[j] = 0  # free start anywhere in the band
    # prev[j] = cost having consumed i query chars and j ref chars
    for i in range(1, n + 1):
        cur = {}
        lo, hi = max(0, i + diag - band), min(m, i + diag + band)
        for j in range(lo, hi + 1):
            best = INF
            if j - 1 in prev:
                best = prev[j - 1] + (0 if query[i - 1] == ref[j - 1] else 1)
            if j in prev:
                best = min(best, prev[j] + 1)  # query base with no ref partner
            if j - 1 in cur:
                best = min(best, cur[j - 1] + 1)
            if best < INF:
                cur[j] = best
        if not cur:
            return 0.0
        prev = cur
    cost = min(prev.values())
    return max(0.0, (n - cost) / n)


class Reference:
    def __init__(self, entries: List[Tuple[str, str, str]]) -> None:
        self.entries = entries  # (accession, species, amplicon)
        self.index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        for idx, (_, _, seq) in enumerate(entries):
            for pos in range(len(seq) - K + 1):
                self.index[seq[pos:pos + K]].append((idx, pos))
        self.species_count = len({s for _, s, _ in entries})
        self.spelling_merges: List[Dict[str, Any]] = []

    @classmethod
    def load(cls, fasta: Optional[Path] = None) -> "Reference":
        fasta = Path(fasta) if fasta else REF_DIR / "reference.fasta"
        entries = []
        for rec in read_records(fasta):
            acc, _, species = rec.id.partition("|")
            entries.append((acc, species.replace("_", " "), rec.seq))
        human = fasta.with_name("human_contaminant.fasta")
        if human.is_file():  # kept in the same index so a human read is recognised as human
            for rec in read_records(human):
                entries.append((rec.id, "Homo sapiens", rec.seq))
        # One animal recorded under two spellings must not look like two species (it would
        # make every read from it 'ambiguous'). The merge rule lives in guard.py.
        from bioradar.adjudicate import guard
        seqs: Dict[str, str] = {}
        counts: Counter = Counter()
        for _, species, seq in entries:
            seqs.setdefault(species, seq)
            counts[species] += 1
        variants = guard.spelling_variants(seqs, counts)
        canonical = {v["merge"]: v["keep"] for v in variants}
        entries = [(a, canonical.get(sp, sp), q) for a, sp, q in entries]
        ref = cls(entries)
        ref.spelling_merges = variants  # reported by the data guard
        return ref

    def exclude_species(self, names) -> "Reference":
        """A copy without the named species (used to show a documented reference gap)."""
        names = {n.lower() for n in names}
        return Reference([e for e in self.entries if e[1].lower() not in names])

    def _candidates(self, seq: str, strand: str, limit: int = 6) -> List[Tuple[int, int, int, str]]:
        votes: Counter = Counter()
        for i in range(len(seq) - K + 1):
            posting = self.index.get(seq[i:i + K])
            if not posting or len(posting) > POSTING_CAP:
                continue
            for idx, pos in posting:
                votes[(idx, pos - i)] += 1
        return [(idx, diag, v, strand) for (idx, diag), v in votes.most_common(limit)]

    def search(self, seq: str, species_threshold: float = 0.985) -> List[Match]:
        """Best match per species, best first. Empty if nothing is even close.

        Every shortlisted candidate gets a fast ungapped identity. Only the two best
        species that fall short of the species threshold are re-scored with a banded
        gapped alignment, because an insertion or deletion is the one thing the
        ungapped score misreads.
        """
        cands = self._candidates(seq, "+") + self._candidates(revcomp(seq), "-")
        cands.sort(key=lambda c: -c[2])
        scored: Dict[str, Tuple[float, str, str, int, str]] = {}
        for idx, diag, votes, strand in cands[:10]:
            if votes < 3:
                continue
            query = seq if strand == "+" else revcomp(seq)
            acc, species, ref = self.entries[idx]
            lo = max(0, -diag)
            hi = min(len(query), len(ref) - diag)
            same = sum(1 for i in range(lo, hi) if query[i] == ref[i + diag])
            identity = same / len(query)
            prior = scored.get(species)
            if prior is None or identity > prior[0]:
                scored[species] = (identity, acc, strand, diag, species)
        ranked = sorted(scored.values(), key=lambda v: -v[0])
        refined = []
        for rank, (identity, acc, strand, diag, species) in enumerate(ranked):
            if rank < 2 and identity < species_threshold:
                query = seq if strand == "+" else revcomp(seq)
                ref = next(e[2] for e in self.entries if e[0] == acc)
                identity = max(identity, _banded_identity(query, ref, diag))
            refined.append(Match(species, acc, round(identity, 4), strand))
        return sorted(refined, key=lambda m: -m.identity)
