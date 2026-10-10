#!/bin/bash

# make the tree
mkdir -p rarefaction/tree

qiime phylogeny align-to-tree-mafft-fasttree \
	--i-sequences qiime2/loci/asvs/rep-seqs-dada2.qza \
	--o-alignment rarefaction/tree/aligned_representative_seqs.qza \
	--o-masked-alignment rarefaction/tree/masked_aligned_representative_seqs.qza \
	--o-tree rarefaction/tree/unrooted_tree.qza \
	--o-rooted-tree rarefaction/tree/rooted_tree.qza \
	--p-n-threads 1 \
	--verbose

# make the bar plots
mkdir -p rarefaction/viz

qiime taxa barplot \
	--i-table qiime2/loci/asvs/table-dada2.qza \
	--i-taxonomy qiime2/loci/asvs/QIIME_tax_sklearn.qza \
	--m-metadata-file manifest/manifest.tsv \
	--o-visualization rarefaction/viz/barchart.qzv \
	--verbose

# get the depth of the largest one.
MAXDEPTH=$(cut report_data/data2_table2.csv -d, -f4 | sort -rn | head -n1)

# do the rarefaction (set max depth to > max number of reads in exp
qiime diversity alpha-rarefaction \
	--i-table qiime2/loci/asvs/table-dada2.qza \
	--i-phylogeny rarefaction/tree/rooted_tree.qza \
	--p-max-depth $MAXDEPTH \
	--p-steps 10 \
	--m-metadata-file ./manifest/manifest.tsv \
	--o-visualization rarefaction/viz/alpha_rarefaction.qzv \
	--verbose
