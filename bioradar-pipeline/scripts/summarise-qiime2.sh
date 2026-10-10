#!/bin/bash  

# summarise and export  

qiime tools export \
  --input-path ./qiime2/loci/asvs/table-dada2.qza \
  --output-path ./qiime2/loci/asvs

biom convert -i ./qiime2/loci/asvs/feature-table.biom \
  -o ./qiime2/loci/asvs/asv-table.tsv \
  --to-tsv

qiime tools export \
  --input-path ./qiime2/loci/asvs/rep-seqs-dada2.qza \
  --output-path ./qiime2/loci/asvs

qiime feature-table tabulate-seqs \
  --i-data ./qiime2/loci/asvs/rep-seqs-dada2.qza \
  --o-visualization ./qiime2/loci/asvs/rep-seqs-dada2.qzv
