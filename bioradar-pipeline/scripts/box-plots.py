#!/usr/bin/env python

import matplotlib.pyplot as plt
import pandas as pd
import sys

# # Create a boxplot from a seven number summary
def create_box(counter,col):
    '''return boxplot data for a column with ticks each 5 bp'''
    if counter %50 != 0:
        counter = ''
        
    box = {
        'label' : counter,
        'whislo': col[0],    # Bottom whisker position
        'q1'    : col[1],    # First quartile (25th percentile)
        'med'   : col[2],    # Median         (50th percentile)
        'q3'    : col[3],    # Third quartile (75th percentile)
        'whishi': col[4],    # Top whisker position
        'fliers': []        # Outliers
        }
    return box

# tsv files for seven number data
seven_num_fwd = sys.argv[1]
seven_num_rev = sys.argv[2]
df_forward = pd.read_table(seven_num_fwd)
df_reverse= pd.read_table(seven_num_rev)

box_data_forward = df_forward.iloc[[1,3,4,5,7],1:]
box_data_reverse= df_reverse.iloc[[1,3,4,5,7],1:]

boxes_forward = []
for ix, column in enumerate(box_data_forward):
    col = box_data_forward[column].values
    box = create_box(ix, col)
    boxes_forward.append(box)

boxes_reverse= []
for ix, column in enumerate(box_data_reverse):
    col = box_data_reverse[column].values
    box = create_box(ix, col)
    boxes_reverse.append(box)

fig, ax = plt.subplots()
ax.bxp(boxes_forward, showfliers=False)
ax.set_title("Quality plot forward read")
ax.set_ylabel("Quality Scores")
ax.set_xlabel("Read base position")
plt.savefig("report_data/boxplot-forward.png")
plt.close()

fig, ax = plt.subplots()
ax.bxp(boxes_reverse, showfliers=False)
ax.set_title("Quality plot reverse read")
ax.set_ylabel("Quality Scores")
ax.set_xlabel("Read base position")
plt.savefig("report_data/boxplot-reverse.png")
plt.close()
