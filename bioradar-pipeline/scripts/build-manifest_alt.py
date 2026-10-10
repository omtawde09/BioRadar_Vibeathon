#!/usr/bin/env python

import os

base1 = snakemake.input[0]

sample_map = {}

# just forward
list_of_files = []
for (dirpath, dirnames, filenames) in os.walk(base1):
    for filename in filenames:
        if filename.endswith('R1_001.fastq.gz'): 
            # remove trailing slash on dirname
            list_of_files.append(os.sep.join([dirpath[:-1], filename]))

print(list_of_files)
print(len(list_of_files))

with open(snakemake.output[0], 'w') as wf:
    wf.write("sample-id\tforward-absolute-filepath\treverse-absolute-filepath\n")
    for R1 in list_of_files:
        R2 = R1.replace("R1_001", "R2_001")
        sample = os.path.basename(R1).split('_')[:-3][0]
        print(R1)
        print(R2)
        print(sample)
        out = "%s\t%s\t%s\n" % (sample, R1, R2)
        wf.write(out)
