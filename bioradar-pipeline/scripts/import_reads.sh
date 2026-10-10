#!/bin/bash

# import the demultiplexed data using a manifest file
# https://docs.qiime2.org/2021.11/tutorials/importing/#sequence-data-with-sequence-quality-information-i-e-fastq
# test 
mkdir -p qiime2/loci

qiime tools import \
  --type 'SampleData[PairedEndSequencesWithQuality]' \
  --input-path ./manifest/manifest.tsv \
  --output-path ./qiime2/loci/paired-end-demux.qza \
  --input-format PairedEndFastqManifestPhred33V2

# generate a summary
qiime demux summarize \
  --i-data ./qiime2/loci/paired-end-demux.qza \
  --o-visualization ./qiime2/loci/paired-end-demux.qzv

echo "qiime2 visulisations of QC data found in the file:"
echo "qiime2/loci/paired-end-demux.qzv"
