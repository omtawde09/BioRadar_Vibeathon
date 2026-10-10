from jinja2 import Template
import codecs
import csv
import yaml

# read the config file
with open('./config.yaml') as file:
    config = yaml.safe_load(file)

# get the median read length and quality data
with open('./report_data/paired-end-demux.qzv/forward-seven-number-summaries.tsv') as rf:
    seq_len = int(next(rf).split('\t')[-1]) + 1 # add a nt for 0 index

# metadata
metadata = []
with open('./metadata.csv') as rf:
    csv_reader = csv.reader(rf)
    for row in csv_reader:
        metadata.append(row)

# sample counts
counts = []
with open('./report_data/paired-end-demux.qzv/per-sample-fastq-counts.tsv') as rf:
    header = next(rf)
    for row in rf:
        bits = row.strip().split('\t')
        counts.append(bits)

# raw and trimmed reads
untrimmed_reads = open('./report_data/seqs_before_trim.fastq').read()
trimmed_reads = open('./report_data/seqs_after_trim.fastq').read()

# trim summary
trim_summary = open('report_data/trim_summary.txt').read()
   
#create an dict will all data that will be populate the template
project = config['project']
cycles = seq_len
primerf = config['fprimer']
primerr = config['rprimer']

# dada2 settings

tlf = config['trunc-len-f']
tlr = config['trunc-len-r']
mef = config['max-ee-f']
mer = config['max-ee-r']
truncq = config['trunc-q']
chimera = config['chimera-method']

print("==================trunq================")
print(truncq)

# dada2 trim tables
with open('./report_data/data2_table1.csv') as rf:
    header = next(rf)
    data2_table1 = [row for row in csv.reader(rf)]
with open('./report_data/data2_table2.csv') as rf:
    header = next(rf)
    data2_table2 = [row for row in csv.reader(rf)]

# rep-seqs summary
with open('./report_data/rep-seqs-dada2.qzv/descriptive_stats.tsv') as rf:
    header = next(rf)
    rep_seqs = [row.strip().split('\t') for row in rf]

data = {'project': project,
        'cycles':cycles,
        'primerf':primerf,
        'primerr': primerr,
        'metadata': metadata,
        'counts':counts,
        'qcr1': './report_data/boxplot-forward.png',
        'qcr2': './report_data/boxplot-reverse.png',
        'untrimmed_reads': untrimmed_reads,
        'trimmed_reads': trimmed_reads,
        'trim_summary': trim_summary,
        'tlf': tlf,
        'tlr': tlr,
        'mef': mef,
        'mer': mer,
        'truncq': truncq,
        'chimera': chimera,
        'data2_table1': data2_table1,
        'data2_table2': data2_table2,
        'rep_seqs': rep_seqs,
        }

#render the template
with open('./report/report-template.md', 'r') as file:
    template = Template(file.read(),trim_blocks=True)
rendered_file = template.render(
        data
                )

#output the file
output_file = codecs.open("final-report.md", "w", "utf-8")
output_file.write(rendered_file)
output_file.close()
