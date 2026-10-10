#!/bin/bash

# use the fastq file names to create a metadata file
# based on this file format: SAMPLENAME_xxx_R1_001.fastq.gz

# See (for formatting options): xxx

# clear the file if it already exists
> metadata.csv

for seq in fastq_data/*_R1*.fastq.gz; 
	do R1=$(basename "$seq");
	R2=$(echo "$R1" | sed 's/R1_001.fastq.gz/R2_001.fastq.gz/');
	sample=${R1%%_*}; 
	echo $sample $R1 $R2 
	echo "$sample,$R1,$R2" >> metadata.csv;
done
