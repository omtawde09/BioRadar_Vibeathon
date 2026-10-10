#!/bin/bash
#

baser1="_S46_L001_R1_001.fastq.gz"
baser2="_S46_L001_R2_001.fastq.gz"

while read file; do
    sample=$(echo $file | cut -d, -f1)
    label=$(echo $file | cut -d, -f2)
    echo $sample
    cat ${sample}*R1*fastq.gz >> ${label}$baser1
    cat ${sample}*R2*fastq.gz >> ${label}$baser2
    rm -f ${sample}*fastq.gz
done<sites.csv
