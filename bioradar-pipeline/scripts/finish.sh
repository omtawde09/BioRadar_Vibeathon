#/bin/bash

# mv to final directory
mkdir -p final_results

mv manifest/manifest.tsv final_results/
mv qiime2/loci/asvs/asv_count_tax_seqs_summary.csv final_results/
mv qiime2/loci/paired-end-demux.qzv final_results/
mv qiime2/loci/asvs final_results/
mv final-report.pdf final_results/
mv rarefaction/viz/* final_results/
mv report_data/*.png final_results/
cp config.yaml final_results/