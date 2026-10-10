#!/bin/bash
#
# create outputs and write a report with a template
# Not sure if pandoc is the best way?

# this seems to create a directory for some artifacts, need to test each one
# make sure the overlap QC is created this might require the code to be re-run
mkdir -p report_data
qiime tools export --input-path ./qiime2/loci/asvs/rep-seqs-dada2.qzv --output-path report_data/rep-seqs-dada2.qzv
qiime tools export --input-path ./qiime2/loci/asvs/stats-dada2.qzv --output-path report_data/stats-dada2.qzv
qiime tools export --input-path ./qiime2/loci/paired-end-demux.qzv --output-path report_data/paired-end-demux.qzv
qiime tools export --input-path ./qiime2/loci/paired-end-demux-trimmed.qzv --output-path report_data/paired-end-demux-trimmed.qzv
#
# create boxplots
python scripts/box-plots.py \
	report_data/paired-end-demux.qzv/forward-seven-number-summaries.tsv \
	report_data/paired-end-demux.qzv/reverse-seven-number-summaries.tsv

# get the first 3 sequences from the first fastq before and after trimming
first_file=$(basename $(ls ./fastq_data/*.fastq.gz | head -n 1))
echo $first_file > report_data/seqs_before_trim.fastq
zcat ./fastq_data/${first_file} | head -n12  >> report_data/seqs_before_trim.fastq
first_file_trimmed=$(basename $(ls ./fastq_data_trimmed/*.fastq.gz | head -n 1))
echo $first_file_trimmed > report_data/seqs_after_trim.fastq
zcat ./fastq_data_trimmed/${first_file_trimmed} \
    | head -n12  >> report_data/seqs_after_trim.fastq

# trim summary from cutadpat
grep -A1 'Read 1 with adapter:' ./logs/qimme2.trim.log > report_data/trim_summary.txt

# create the data2 tables
python ./scripts/data2_tables.py ./report_data/stats-dada2.qzv/metadata.tsv
