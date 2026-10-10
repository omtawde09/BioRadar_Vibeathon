"""Command line for the relative finder.

    python -m bioradar.relatives lineage                       # fetch NCBI lineage (once)
    python -m bioradar.relatives calibrate                     # leave-one-species-out test
    python -m bioradar.relatives query --seq ACGT... [--obs habitat=freshwater --obs karyotype_2n=48]
    python -m bioradar.relatives query --fasta reads.fa        # first record
    python -m bioradar.relatives sample SRR37521672 --top 10   # top unknowns of a processed sample
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


def _obs(pairs: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for pair in pairs or []:
        key, _, value = pair.partition("=")
        try:
            out[key.strip()] = float(value) if "." in value else int(value)
        except ValueError:
            out[key.strip()] = value.strip()
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="BioRadar relative finder")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lineage")
    cal = sub.add_parser("calibrate")
    cal.add_argument("--limit", type=int)
    q = sub.add_parser("query")
    q.add_argument("--seq")
    q.add_argument("--fasta")
    q.add_argument("--obs", action="append", default=[])
    s = sub.add_parser("sample")
    s.add_argument("sample_id")
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "lineage":
        from bioradar.relatives import lineage
        print(lineage.fetch())
        print(json.dumps(lineage.meta(), indent=2))
        return 0
    if args.cmd == "calibrate":
        from bioradar.relatives import calibrate
        doc = calibrate.run(limit=args.limit)
        print(json.dumps(doc["summary"], indent=2))
        return 0
    if args.cmd == "query":
        from bioradar.relatives.model import finder
        seq = args.seq
        if args.fasta:
            from bioradar.adjudicate.seqio import read_records
            seq = next(iter(read_records(args.fasta))).seq
        if not seq:
            parser.error("give --seq or --fasta")
        print(json.dumps(finder().speculate(seq, _obs(args.obs)), indent=2))
        return 0
    from bioradar.relatives.service import sample_hypotheses
    doc = sample_hypotheses(args.sample_id, top=args.top, force=args.force)
    for h in doc["hypotheses"]:
        hyp = h["hypothesis"] or {}
        print("{:>6} reads  closest {:<32} cos {:.3f}  -> {} {} (support {})".format(
            h["reads"], h["closest_species"]["species"], h["closest_species"]["cosine"],
            hyp.get("rank"), hyp.get("taxon"), hyp.get("support")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
