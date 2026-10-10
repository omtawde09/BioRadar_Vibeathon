![](./report/eDNA.png)

# Summary eDNA report
This report summarises the output from a eDNA pipeline based on QIIME2 for
project {{ project }}.     

## Raw sequence data  
The maximum sequence length for reads in the `fastq_data`
folder was: {{ cycles }}bp.  

## Primers
The following primer sequences were listed in the `config.yaml` file
used to setup the pipeline. These primers are removed from the reads
before downstream processing.  

```
forward primer: 5'-{{ primerf }}-3'
reverse primer: 5'-{{ primerr }}-3'
```

## Metadata  
The following metadata was supplied in `metadata.csv`. This file maps
samples to the sequencing data located in the `fastq_data` folder.  
Note only for the R1 file name is shown.  

| Sample | R1 filename |
|--------|--------------|
{% for meta in metadata %}
| {{ meta[0] }} | {{ meta[1] }} |
{% endfor %}

Based on the metadata supplied the following raw sequence counts were
observed for each sample (this represents the number of sequenced 
read pairs).  

Table 2. Raw sequence counts for each sample.  

| Sample ID | Raw sequence count |
|-----------|--------------------|
{% for count in counts %}
| {{ count[0] }} | {{ count[1] }} | 
{% endfor %}


The QC plot for the R1 forward read is shown in the figure below. Note a 
quality score (y-axis) of >20 corresponds to base call accuracy of >99%.  
The box plot shows the 25th, 50th (median), and 75th percentiles. The 
whiskers indicate the min and max values. The median quality score for 
each base is shown by the orange bar.    

![Figure 1: QC plot of foward R1 read]({{ qcr1 }})

And the reverse R2 read.  

![Figure 2: QC plot of reverse R2 read]({{ qcr2 }})


## Checking for primer sequences   
An important sanity check is to confirm that primer sequences are being correctly
identified and removed from the reads before downstream processing. If the primers
are not correctly removed this will result in taxonomic errors (so it is important 
to check that this is working correctly). The panel below 
shows the first 3 reads before the primers sequences are removed by
cutadapt. The forward primer (5-{{ primerf }}-3) should be 
located at the 5' end of these sequences (note that sequence errors often occur
at the very 5' end of the read). The first line shows the file these sequences
were obtained from. A full description of the fastq format
can be found [here](https://en.wikipedia.org/wiki/FASTQ_format).  

```
{{ untrimmed_reads }}
```

The next panel is after cutadapt has removed the primers.  

```
{{ trimmed_reads }}
```

A summary of the primer trimming log file is shown below, the full file can be found
in `logs/qimme2.trim.log`. We would expect a very high percentage (>90%) of the
reads to contain primers otherwise it could indicate PCR issues. If 
any of these outputs show a low percentage please check the 
`logs/qimme2.trim.log` file to identify the problematic file.  

```
{{ trim_summary }}
```

## Denoising with DADA2  
This step filters out noisy sequences, correct errors in marginal sequences,
removes chimeric sequences, removes singletons, joins denoised paired-end reads,
and then de-replicates these sequences. The de-replicated sequences are used to
assign taxonomy and generate taxonomic counts.  

For target loci with variable length it is important to limit sequence truncation
(in this case `p-trunc-len-f` and `p-trunc-len-r` should be set to 0), otherwise
this could create a
sequence length bias. For fixed length loci the trimming parameters need to be 
adjusted based the sequence quality profile (Figures 1 and 2) to ensure that the
read overlaps includes high quality calls, whilst maximising the sequence overlap.
The R2 read is normally trimmed more aggressively.   

The settings used in this run were (from the `config.yaml` file):  

```
--p-trunc-len-f {{ tlf }} 
--p-trunc-len-r  {{ tlr }}
--p-max-ee-f {{ mef }}
--p-max-ee-r {{ mer }}
--p-trunc-q {{ truncq }}
--consensus-method: {{ chimera }}
```

A full explanation of the above settings is available [here](https://docs.qiime2.org/2022.2/plugins/available/dada2/denoise-paired/).  

The tables below summarise the results of the DADA2 filtering and de-noising steps. 
The de-noising and chimera removal steps should only remove a small proportion (<30%)
of reads otherwise the above DADA2 settings may need to be adjusted. The actual
number of sequences retained depends on several factors, such as sequence error
profile and paired-end read overlap length.  

Table 3. De-noising results from the *dada2* algorithm.  

| Sample | Input | Filtered | Passed filter (%) | de-noised |
|--------|-------|----------|-------------------|-----------|
{% for row in data2_table1 %}
| {{ row[0] }} | {{ row[1] }} | {{ row[2] }} |{{ row[3] }} |{{ row[4] }} |
{% endfor %}

The read merging and de-noising summary is below. Note the final
non-chimeric sequences are used for assigning taxonomy and generating 
the taxonomy counts for each sample.

Table 4. Final non-chimeric sequence counts.  

| Sample | Merged       | Input merged (%) | Non-chimeric | Non-chimeric (%) |
|--------|--------------|------------------|--------------|------------------|
{% for row in data2_table2 %}
| {{ row[0] }} | {{ row[1] }} | {{ row[2] }} |{{ row[3] }} |{{ row[4] }} |
{% endfor %}

## Representative eDNA sequences identified  
The following summary statics describe the representative sequences used to 
assign taxonomy and taxonomic counts that make up the eDNA profile.   

Table 5. Summary metrics for the representative sequences used for taxonomic
assignment (min, max, mean, range and standard deviation are base-pairs).   

| Metric | value  |
| -----  | ------ |
{% for row in rep_seqs %}
| {{ row[0] }} | {{ row[1] }} |
{% endfor %}

## Final eDNA taxonomic count table
The final spreadsheet (CSV file) of taxonomic counts across the samples
can be found at the following folder paths: `final_results/asv_count_tax_seqs_summary.csv`.  
Each sample is represented by a column in the spreadsheet showing the number
of sequences for each species (rows). Note these are raw sample counts 
(they have not been normalised by the number of reads obtained for each sample).  

The columns descriptions in the final spreadsheet are shown below in Table 6.  

Table 6. Column descriptions for `asv_count_tax_seqs.csv`.  

| Column             | Description                                           |
| ------------------ | ----------------------------------------------------- |
| Feature_ID         | Hash identification for reference sequence            |
| Taxon              | Taxonomic breakdown of reference sequence             |
| Taxa_confidence    | Confidence of taxonomic assignment                    |
| Reference_variants | The number of ASVs variants for this species |
| reference sequence | The reference DNA sequence use to make the assignment |

## Software versions used
A complete list of packages and versions is available in:                     
`./env/qiime2-2022.2-py38-linux-conda.yml`  

This pipeline was written by Dave Wheeler (DPI's Chief Scientist Unit). For any
issues please make contact: dave.wheeler@dpi.nsw.gov.au
