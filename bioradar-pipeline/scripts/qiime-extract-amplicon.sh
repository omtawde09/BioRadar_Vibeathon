#!/bin/bash

# using UNITE for ITS

# primers 
qiime feature-classifier extract-reads \
  --i-sequences ./database/qiime2-qza/MIDORI2_UNIQ_NUC_GB253_srRNA_QIIME.fasta.qza \
	--p-f-primer ACACCGCCCGTCAYYCT \
  --p-r-primer CTTCCGGTAYACTTACCRTG \
	--o-reads ./database/qiime2-qza/MIDORI2_UNIQ_NUC_GB253_srRNA_QIIME.fasta.extracts.qza \
  --p-n-jobs 24

qiime feature-classifier fit-classifier-naive-bayes \
	--i-reference-reads ./database/qiime2-qza/MIDORI2_UNIQ_NUC_GB253_srRNA_QIIME.fasta.extracts.qza \
	--i-reference-taxonomy ./database/qiime2-qza/MIDORI2_UNIQ_NUC_GB253_srRNA_QIIME.taxon.qza \
	--o-classifier ./database/qiime2-qza/MIDORI2_UNIQ_NUC_GB253_srRNA_QIIME-classifier.qza
