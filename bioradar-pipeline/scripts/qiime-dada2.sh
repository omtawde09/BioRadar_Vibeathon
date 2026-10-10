#!/bin/bash  

mkdir -p ./qiime2/loci/asvs/

# p-trunc-len-f -> If 0 is provided, no truncation 

echo "Using the following DADA2 params:"
echo "--p-trunc-len-f $1" 
echo "--p-trunc-len-r $2" 
echo "--p-max-ee-f $3" 
echo "--p-max-ee-r $4" 
echo "--p-trunc-q $5" 
echo "--p-chimera-method $6"

qiime dada2 denoise-paired \
    --i-demultiplexed-seqs ./qiime2/loci/paired-end-demux-trimmed.qza \
    --p-n-threads 12 \
    --p-trunc-len-f $1 \
    --p-trunc-len-r $2 \
    --p-max-ee-f $3 \
    --p-max-ee-r $4 \
    --p-trunc-q $5 \
    --p-chimera-method $6 \
    --o-table ./qiime2/loci/asvs/table-dada2.qza \
    --o-representative-sequences ./qiime2/loci/asvs/rep-seqs-dada2.qza \
    --o-denoising-stats ./qiime2/loci/asvs/stats-dada2.qza \
    --verbose >> ./logs/dada2.log 2>&1

qiime metadata tabulate \
    --m-input-file ./qiime2/loci/asvs/stats-dada2.qza \
    --o-visualization ./qiime2/loci/asvs/stats-dada2.qzv
