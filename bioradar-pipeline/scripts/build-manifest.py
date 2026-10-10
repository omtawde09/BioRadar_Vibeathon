#!/usr/bin/env python
import csv
import os

# needs config
base = os.getcwd() + "/fastq_data/"

mappings = {}
with open("metadata.csv") as rf:
    csv_reader = csv.reader(rf)
    for row in csv_reader:
        sample, r1, r2 = row
        assert sample not in mappings
        mappings[sample] = (base+r1, base+r2)
    
print("using these mappings")
print(mappings)

try:
    os.mkdir(os.path.join(os.getcwd(), "manifest"))
except OSError:
    print("manifest directory exists, nothing to do")

with open('./manifest/manifest.tsv', 'w') as wf:
    wf.write("sample-id\tforward-absolute-filepath\treverse-absolute-filepath\n")
    for sample in mappings:
        out = "%s\t%s\t%s\n" % (sample, mappings[sample][0], 
                mappings[sample][1])
        wf.write(out)
