#!/usr/bin/bashb

# convert the fasta and taxonomy text files into qiime qza objects
# for training
# see https://github.com/colinbrislawn/unite-train/blob/main/workflow/Snakefile for hints

# ref seqs
qiime tools import --type FeatureData[Sequence] \
	--input-path ../db/unite/sh_refs_qiime_ver9_99_29.11.2022.fasta \
	--output-path ../db/unite/sh_refs_qiime_ver9_99_29.11.2022.qza
# taxa
qiime tools import --type FeatureData[Taxonomy] \
	--input-format HeaderlessTSVTaxonomyFormat \
	--input-path ../db/unite/sh_taxonomy_qiime_ver9_99_29.11.2022.txt \
	--output-path ../db/unite/sh_taxonomy_qiime_ver9_99_29.11.2022.qza
