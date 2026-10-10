#!/bin/bash
# https://docs.qiime2.org/2019.10/tutorials/feature-classifier/
# https://github.com/allenlab/QIIME2_ITS_ASV_protocol/blob/master/README.md 
# train the classifier using our region

# cpus
# Upstream pinned this to 4 because classify-sklearn holds a copy of the
# classifier per job, and the shipped MIDORI2 model unpacks to ~1.9 GB. The
# India-curated COI classifier is amplicon-extracted and 9.5 MB, so the memory
# argument no longer applies -- but keep a cap, since a full-length classifier
# would still blow up a laptop.
ncpu=$(grep -c ^processor /proc/cpuinfo)
if [ "$ncpu" -gt 8 ]; then
    ncpu=8
fi

qiime feature-classifier classify-sklearn \
  --p-n-jobs $ncpu \
  --i-classifier $1 \
  --i-reads ./qiime2/loci/asvs/rep-seqs-dada2.qza \
  --o-classification ./qiime2/loci/asvs/QIIME_tax_sklearn.qza

echo "exporting..."

qiime tools export \
  --input-path ./qiime2/loci/asvs/QIIME_tax_sklearn.qza \
  --output-path ./qiime2/loci/asvs/

# rename
#mv ./qiime2/loci/asvs/taxonomy.tsv ./qiime2/loci/asvs/Midori_trained_taxonomy.tsv
