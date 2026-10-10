"""Sample adjudication: from a real public sequence file to an honest answer.

This package is deliberately separate from the QIIME2/DADA2 pipeline. It is a
lightweight, pure-Python path that reads sequence *content* (never file names),
decides what to keep, drop or send for review, and says why for every decision.

    fetch      download the real public dataset + reference, verify checksums
    thresholds every tunable number, in one file, with its rationale
    seqio      FASTA / FASTQ reading and dereplication
    reference  the 12S reference list and the nearest-match search
    quality    per-sequence QC with a written reason for every drop
    adjudicate kept / dropped / unknown, mixed-sample split, sample verdict
    guard      record-level data guard (duplicate ID, GPS, date, spelling)
    alerts     invasive-species danger levels and the alert event
    seasons    same-site seasonal comparison
    report     the one-page officer PDF
"""
