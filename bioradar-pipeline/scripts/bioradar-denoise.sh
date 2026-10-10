#!/bin/bash
#
# BioRadar denoiser dispatcher.
#
# Upstream calls qiime-dada2.sh directly. DADA2 models sequencing error as a
# function of the quality score, so it cannot process data submitted with
# quality stripped -- several public Indian datasets (PRJNA1296846,
# PRJNA1040471) carry a single quality value for every base and fail with
# "Error rates could not be estimated", which reads like a read-count problem
# and is not one.
#
# vsearch OTU clustering ignores quality entirely, so it recovers those
# datasets. It is coarser -- 97%-identity OTUs rather than exact amplicon
# sequence variants -- so DADA2 stays the default wherever it works.
#
# Both paths emit the same three artifacts, so everything downstream is
# unchanged:
#   qiime2/loci/asvs/table-dada2.qza
#   qiime2/loci/asvs/rep-seqs-dada2.qza
#   qiime2/loci/asvs/stats-dada2.qzv
#
# usage: bioradar-denoise.sh <denoiser> <trunc_f> <trunc_r> <maxee_f> <maxee_r> <truncq> <chimera>

set -euo pipefail

DENOISER="${1:-dada2}"
shift || true

mkdir -p ./qiime2/loci/asvs/ ./logs

if [[ "$DENOISER" != "vsearch" ]]; then
    echo "denoiser: DADA2"
    exec bash scripts/qiime-dada2.sh "$@"
fi

echo "denoiser: vsearch OTU clustering (97% identity)"
echo "  chosen because this dataset's quality scores cannot support DADA2"

PERC_IDENTITY="${BIORADAR_OTU_IDENTITY:-0.97}"
# q2-vsearch caps --p-threads at 8 and does not scale much past 4 anyway.
THREADS="$(grep -c ^processor /proc/cpuinfo)"
# An `if`, not `[ ... ] && ...`: under `set -e` a false test is a non-zero exit
# and would kill the script on any machine with 8 cores or fewer.
if [ "$THREADS" -gt 8 ]; then
    THREADS=8
fi

echo "== merging read pairs =="
qiime vsearch merge-pairs \
    --i-demultiplexed-seqs ./qiime2/loci/paired-end-demux-trimmed.qza \
    --p-threads "$THREADS" \
    --o-merged-sequences ./qiime2/loci/merged.qza \
    >> ./logs/vsearch.log 2>&1

# Lenient on purpose: the whole reason we are here is that the quality scores
# carry no information, so filtering on them would either drop everything or
# nothing. Length filtering does the real work.
echo "== quality filter (lenient) =="
qiime quality-filter q-score \
    --i-demux ./qiime2/loci/merged.qza \
    --p-min-quality 4 \
    --p-quality-window 3 \
    --o-filtered-sequences ./qiime2/loci/filtered.qza \
    --o-filter-stats ./qiime2/loci/filter-stats.qza \
    >> ./logs/vsearch.log 2>&1

echo "== dereplicating =="
qiime vsearch dereplicate-sequences \
    --i-sequences ./qiime2/loci/filtered.qza \
    --o-dereplicated-table ./qiime2/loci/derep-table.qza \
    --o-dereplicated-sequences ./qiime2/loci/derep-seqs.qza \
    >> ./logs/vsearch.log 2>&1

echo "== clustering at ${PERC_IDENTITY} identity =="
qiime vsearch cluster-features-de-novo \
    --i-table ./qiime2/loci/derep-table.qza \
    --i-sequences ./qiime2/loci/derep-seqs.qza \
    --p-perc-identity "$PERC_IDENTITY" \
    --p-threads "$THREADS" \
    --o-clustered-table ./qiime2/loci/clustered-table.qza \
    --o-clustered-sequences ./qiime2/loci/clustered-seqs.qza \
    >> ./logs/vsearch.log 2>&1

echo "== removing chimeras =="
qiime vsearch uchime-denovo \
    --i-table ./qiime2/loci/clustered-table.qza \
    --i-sequences ./qiime2/loci/clustered-seqs.qza \
    --o-chimeras ./qiime2/loci/chimeras.qza \
    --o-nonchimeras ./qiime2/loci/nonchimeras.qza \
    --o-stats ./qiime2/loci/uchime-stats.qza \
    >> ./logs/vsearch.log 2>&1

qiime feature-table filter-features \
    --i-table ./qiime2/loci/clustered-table.qza \
    --m-metadata-file ./qiime2/loci/nonchimeras.qza \
    --o-filtered-table ./qiime2/loci/asvs/table-dada2.qza \
    >> ./logs/vsearch.log 2>&1

qiime feature-table filter-seqs \
    --i-data ./qiime2/loci/clustered-seqs.qza \
    --m-metadata-file ./qiime2/loci/nonchimeras.qza \
    --o-filtered-data ./qiime2/loci/asvs/rep-seqs-dada2.qza \
    >> ./logs/vsearch.log 2>&1

# The QC report reads DADA2's nine-column stats table out of stats-dada2.qzv
# (scripts/data2_tables.py). `feature-table summarize` produces a valid
# visualization but with different innards, so the report dies. Build the same
# nine columns from the numbers vsearch actually produced instead.
echo "== building denoising stats =="
qiime tools export \
    --input-path ./qiime2/loci/filter-stats.qza \
    --output-path ./qiime2/loci/filter-stats-export \
    >> ./logs/vsearch.log 2>&1

qiime tools export \
    --input-path ./qiime2/loci/asvs/table-dada2.qza \
    --output-path ./qiime2/loci/table-export \
    >> ./logs/vsearch.log 2>&1

biom convert \
    -i ./qiime2/loci/table-export/feature-table.biom \
    -o ./qiime2/loci/table-export/table.tsv --to-tsv \
    >> ./logs/vsearch.log 2>&1

python - <<'PYSTATS'
import csv
import os

# Per-sample retained reads, from the final clustered non-chimeric table.
retained = {}
table = "./qiime2/loci/table-export/table.tsv"
if os.path.isfile(table):
    with open(table) as handle:
        rows = [r for r in handle if not r.startswith("# ")]
    reader = csv.reader(rows, delimiter="\t")
    header = next(reader, [])[1:]
    totals = [0.0] * len(header)
    for row in reader:
        for index, value in enumerate(row[1:]):
            totals[index] += float(value or 0)
    retained = {s: int(t) for s, t in zip(header, totals)}

# Input/filtered counts, from the quality-filter step.
inputs = {}
stats = "./qiime2/loci/filter-stats-export/stats.csv"
if os.path.isfile(stats):
    with open(stats) as handle:
        for row in csv.DictReader(handle):
            sample = row.get("sample-id") or row.get("id") or ""
            try:
                inputs[sample] = (
                    int(float(row.get("total-input-reads", 0))),
                    int(float(row.get("total-retained-reads", 0))),
                )
            except ValueError:
                continue

columns = [
    "input", "filtered", "percentage of input passed filter", "denoised",
    "merged", "percentage of input merged", "non-chimeric",
    "percentage of input non-chimeric",
]
with open("./qiime2/loci/vsearch-stats.tsv", "w", newline="") as out:
    writer = csv.writer(out, delimiter="\t")
    writer.writerow(["id"] + columns)
    writer.writerow(["#q2:types"] + ["numeric"] * len(columns))
    for sample in sorted(set(retained) | set(inputs)):
        total_in, filtered = inputs.get(sample, (retained.get(sample, 0),) * 2)
        kept = retained.get(sample, 0)
        pct = lambda n: round(100.0 * n / total_in, 2) if total_in else 0.0
        # vsearch has no separate denoise step; merged == filtered here, and the
        # clustered non-chimeric count is the meaningful survivor number.
        writer.writerow(
            [sample, total_in, filtered, pct(filtered), filtered,
             filtered, pct(filtered), kept, pct(kept)]
        )
print("wrote vsearch-stats.tsv")
PYSTATS

qiime metadata tabulate \
    --m-input-file ./qiime2/loci/vsearch-stats.tsv \
    --o-visualization ./qiime2/loci/asvs/stats-dada2.qzv \
    >> ./logs/vsearch.log 2>&1

echo "vsearch denoising complete"
