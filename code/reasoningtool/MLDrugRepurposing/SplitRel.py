import csv
import pandas as pd
import argparse as ap
import numpy as np
import time


# The following parses the arguments entered into the terminal:
parser = ap.ArgumentParser(description='This will take a csv containing SemMedDB predicate tuples and break them up')
parser.add_argument('--f', type=str, nargs=1, help = 'Input the file path for the csv for which you wish to break up')
parser.add_argument('--s', type=str, nargs=1, help = 'Input the file path for where you wish to save the new csv')

args = parser.parse_args()

# specifies the size of the batches to load into pandas
batchSize = 1000 

# This breaks up 
def split_df(df, columns, split_val='|'):
    df = df.assign(**{column:df[column].str.split(split_val) for column in columns})
    diff_columns = df.columns.difference(columns)
    lengths = df[columns[0]].str.len()
    if sum(lengths > 0) == len(df):
        df2 = pd.DataFrame({column:np.repeat(df[column].values, df[columns[0]].str.len()) for column in diff_columns})
        df2 = df2.assign(**{column:np.concatenate(df[column].values) for column in columns}).loc[:, df.columns]
        return df2
    else:
        df2 = pd.DataFrame({column:np.repeat(df[column].values, df[columns[0]].str.len()) for column in diff_columns})
        df2 = df2.assign(**{column:np.concatenate(df[column].values) for column in columns}).append(df.loc[lengths==0, diff_columns]).fillna('').loc[:, df.columns]
        return df2

header = None
c = 0
for df in pd.read_csv(args.f[0], header=0, chunksize=batchSize, iterator=True):
    c += 1
    #df3 = df.assign(subject_cui=df.subject_cui.str.split('|')).assign(subject_name=df.subject_name.str.split('|')).assign(object_cui=df.object_cui.str.split('|')).assign(object_name=df.object_name.str.split('|'))
    df_left = split_df(df, ['subject_cui','subject_name'])
    df2 = split_df(df_left, ['object_cui','object_name'])
    for r in range(len(df2['subject_cui'])):
        sKey = df2['subject_cui'][r] + df2['subject_name'][r]
        oKey = df2['object_cui'][r] + df2['object_name'][r]
    if header is None:
        header = list(df.columns)
        df3 = pd.DataFrame([header], columns = df.columns)
        df2 = pd.concat([df3,df2], ignore_index=True)
    df2.to_csv(args.s[0], header = None, index=None, mode='a') # appends the resulting dataframe to a csv file

