#!/bin/bash

#conda activate cutadaptenv

fwd=GTGYCAGCMGCCGCGGTAA
fwdrc=TTACCGCGGCKGCTGRCAC
rev=GGACTACNVGGGTWTCTAAT
revrc=ATTAGAWACCCBNGTAGTCC
outdir=finaldata/16S/trimmed

R1=$1
echo $R1
R2=$(echo $R1 | sed 's/R1_001.fastq.gz/R2_001.fastq.gz/g')
echo $R2
outpath1=$outdir/$(basename $R1 | sed 's/fastq.gz/trimmed.fastq.gz/g')
outpath2=$outdir/$(basename $R2 | sed 's/fastq.gz/trimmed.fastq.gz/g')

cutadapt -a ^${fwd}...${revrc} -A ^${rev}...${fwdrc} -o $outpath1 -p outpath2 $R1 $R2
echo "============"
