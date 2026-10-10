#!/usr/bin/env python
# coding: utf-8
import pandas as pd
import sys

# Create tables from data2 output

target = sys.argv[1]
# drop the first row as this is just header info
df = pd.read_table(target).tail(-1)

df1 = df.iloc[:,:5]
df1.columns = ['Sample', 'Input', 'Filtered','Passed filter (%)', 'de-noised']
df1.head()
df1.to_csv('report_data/data2_table1.csv', index=False)

# second half of table
df2 = df.iloc[:,[0,5,6,7,8]]
df2.columns = ['Sample', 'Merged', 'Input merged (%)','Non-chimeric', 'Non-chimeric (%)']
df2.to_csv('report_data/data2_table2.csv', index=False)
