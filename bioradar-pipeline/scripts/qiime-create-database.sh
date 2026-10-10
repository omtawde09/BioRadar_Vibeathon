#!/usr/bin/bash

mkdir -p ./database/qiime2-qza

# convert the MIDORI 12S taxonomy to a qiime qza file
qiime tools import \
    --type FeatureData[Taxonomy] \
    --input-path $1 \
    --input-format HeaderlessTSVTaxonomyFormat \
    --output-path ./database/qiime2-qza/database.taxon.qza

# convert the MIDORI 12S taxonomy fasta to a qiime qza file
qiime tools import \
    --input-path $2 \
    --output-path ./database/qiime2-qza/database.fasta.qza \
    --type FeatureData[Sequence]


# extract amplicon
# primers 
qiime feature-classifier extract-reads \
  --i-sequences ./database/qiime2-qza/database.fasta.qza \
	--p-f-primer $3 \
  --p-r-primer $4 \
	--o-reads ./database/qiime2-qza/database.fasta.extracts.qza \
  --p-n-jobs 24

qiime feature-classifier fit-classifier-naive-bayes \
	--i-reference-reads ./database/qiime2-qza/database.fasta.extracts.qza \
	--i-reference-taxonomy ./database/qiime2-qza/database.taxon.qza \
	--o-classifier ./database/qiime2-qza/QIIME-classifier.qza
