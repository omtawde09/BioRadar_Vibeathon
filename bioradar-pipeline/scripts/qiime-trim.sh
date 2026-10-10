#!/bin/bash

# cores
ncpu=$(grep -c ^processor /proc/cpuinfo)

#  IUPAC codes
IUPACf="ACGTacgtRYMKSWHBVDNrymkswhbvdn"
IUPACr="TGCAtgcaYRKMSWDVBHNyrkmswdvbhn"

# issue with running out of space this is not working somehow
mkdir -p logs
#tmp=$(pwd)/tmp
#mkdir -p $tmp
#export TMPDIR=$tmp
#echo "temp files saving to $tmp"

# primers
fprimer=$1
fprimer_rc=$(echo $fprimer | tr $IUPACf $IUPACr | rev)
rprimer=$2
rprimer_rc=$(echo $rprimer | tr $IUPACf  $IUPACr | rev)

echo "Forward read trimming"
echo ^${fprimer}...${rprimer_rc}
echo "Reverse read trimming"
echo ^${rprimer}...${fprimer_rc}

# trim paramas
er=$3 # 0.1
ol=$4 # 3
echo "Using p-error-rate=$er and p-overlap=$ol"

qiime cutadapt trim-paired \
  --i-demultiplexed-sequences ./qiime2/loci/paired-end-demux.qza  \
  --p-cores $ncpu \
  --p-adapter-f ^${fprimer}...${rprimer_rc} \
  --p-adapter-r ^${rprimer}...${fprimer_rc} \
  --p-error-rate $er \
  --p-overlap $ol \
  --p-discard-untrimmed \
  --verbose \
  --o-trimmed-sequences ./qiime2/loci/paired-end-demux-trimmed.qza > ./logs/qimme2.trim.log 2>&1

# visualise the results  
qiime demux summarize \
  --i-data ./qiime2/loci/paired-end-demux-trimmed.qza \
  --o-visualization ./qiime2/loci/paired-end-demux-trimmed.qzv

# export as fastq to check trimming
mkdir -p fastq_data_trimmed/
qiime tools extract \
  --input-path ./qiime2/loci/paired-end-demux-trimmed.qza \
  --output-path fastq_data_trimmed/

mv fastq_data_trimmed/*/data/*fastq.gz fastq_data_trimmed/
