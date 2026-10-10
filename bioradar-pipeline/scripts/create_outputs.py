#!/usr/bin/env python
from Bio import SeqIO
import csv
import pandas as pd
import numpy as np

# script to output the final tables

asv_table = pd.read_table("./qiime2/loci/asvs/asv-table.tsv", header=1)
asv_table.rename(columns={'#OTU ID': 'Feature_ID'}, inplace=True)
print("The first 5 rows of the ASV table looks like this:")
print(asv_table.head())

midori = pd.read_table('./qiime2/loci/asvs/taxonomy.tsv', header=0)
midori.rename(columns={"Feature ID": "Feature_ID"}, inplace=True)
print()
print("The first 5 rows of the taxa table looks like this:")
print(midori.head())

output = pd.merge(asv_table, midori, on="Feature_ID", how="left") 
print()
print("The first 5 rows of the final table looks like this:")
print(output.head())

# save
output.to_csv("qiime2/loci/asvs/asv_count_tax.csv", index=False)

# add sequences
seq_dict = {}
with open("qiime2/loci/asvs/dna-sequences.fasta") as rf:
    for rec in SeqIO.parse(rf, 'fasta'):
        seq_dict[rec.id] = str(rec.seq)

with open("qiime2/loci/asvs/asv_count_tax_seqs.csv", "w") as wf:
    csv_writer = csv.writer(wf)
    with open("qiime2/loci/asvs/asv_count_tax.csv") as rf:
        csv_reader = csv.reader(rf)
        header = next(csv_reader)
        header.append("reference sequence")
        csv_writer.writerow(header)
        for row in csv_reader:
            hash_id = row[0]
            ref_seq = seq_dict[hash_id]
            row.append(ref_seq)
            csv_writer.writerow(row)
# groupby species and summarise table
df = pd.read_csv("qiime2/loci/asvs/asv_count_tax_seqs.csv")

# counts the number of ref variants the mean confidence for these
spec_info = {}
# collect mean confidence
counter=1
for index, row in df.iterrows():
    spec = row[-3]
    if spec == 'Unassigned':
        spec = spec+str(counter)
        counter+=1
        df.loc[index,'Taxon'] = spec
    prob = float(row[-2])
    seq = row[-1]
    if spec in spec_info:
        # prob
        spec_info[spec][0].append(prob)
    else:
        spec_info[spec] = [[prob],seq]

# for checking during testing
df.to_csv("qiime2/loci/asvs/tmp1.csv")

# output csv - all rows
new_df = df.iloc[:,1:-2].groupby(['Taxon']).sum()
new_df['Taxon'] = new_df.index

#new_df.reindex()
new_df['Taxa_confidence'] = new_df.apply(lambda x: np.mean(spec_info[x['Taxon']][0]), axis=1)
new_df['Reference_variants'] = new_df.apply(lambda x: len(spec_info[x['Taxon']][0]), axis=1)
new_df['reference_sequence']= new_df.apply(lambda x: spec_info[x['Taxon']][1], axis=1)

# drop the redundant taxa col
new_df.drop(['Taxon'], axis=1, inplace=True)
print("table after groupby taxa")
print(new_df.head())
new_df.sort_values(['Taxon'], inplace=True, ascending=False)
new_df.to_csv("qiime2/loci/asvs/asv_count_tax_seqs_summary.csv")
