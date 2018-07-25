################################################
# WARNING: semmeddb, umls, and semrep docker   #
# containers must be up and running on         #
# rtxdev.saramsey.org in order for this to run #
################################################


import requests_cache
import time
import pandas
import numpy
import csv
import sys
import os
# Setup path to import SemMedInterface
new_path = os.path.join(os.getcwd(), '..', 'SemMedDB')
sys.path.insert(0, new_path)

# parse arguments from terminal
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--source", type=str, help="The filename or path to the source node list csv", default='drugs.csv')
parser.add_argument("-t", "--target", type=str, help="The filename or path to the target node list csv", default='diseases.csv')
args = parser.parse_args()

from SemMedInterface import SemMedInterface

# Connects to SemMedDB and UMLS mysql instances as well as semrep api
sms = SemMedInterface()

# Load the source nodes
df = pandas.read_csv(args.source)
df = df.sample(frac=1,random_state=1123581321).reset_index(drop=True)

df['cuis'] = [[]]*len(df)
df['cuis'] = df['cuis'].astype(object)

c = 0
d = 0
print('Building Source Cui Map...')
# runs through the curie ids
for a in range(len(df['id'])):
    b1 = sms.get_cui_for_id(df['id'][a])
    b2 = sms.get_cui_for_name(df['name'][a])
    # builds mapping from id match first
    if b1 is not None:
        d += 1
        df.at[a,'cuis'] = b1
    # if no id match it found it then builds mapping from natural language name
    elif b2 is not None:
        d += 1
        df.at[a,'cuis'] = b2
    c += 1
    # This just prints out progress every 10% uncomment if you want this
    #if c % int(len(df['id'])/10 + 1) == 0:
    #    print(c/len(df['id']))

df.to_csv('data/source_map.csv', index=False)

# Load the target nodes
df = pandas.read_csv(args.target)
df = df.sample(frac=1,random_state=1123581321).reset_index(drop=True)

df['cuis'] = [[]]*len(df)
df['cuis'] = df['cuis'].astype(object)

c = 0
d = 0
print('Building Target Cui Map...')
# runs through the curie ids
for a in range(len(df['id'])):
    b1 = sms.get_cui_for_id(df['id'][a])
    b2 = sms.get_cui_for_name(df['name'][a])
    # builds mapping from id match first
    if b1 is not None:
        d += 1
        df.at[a,'cuis'] = b1
    # if no id match it found it then builds mapping from natural language name
    elif b2 is not None:
        d += 1
        df.at[a,'cuis'] = b2
    c += 1
    # This just prints out progress every 10% uncomment if you want this
    #if c % int(len(df['id'])/10 + 1) == 0:
    #    print(c/len(df['id']))

df.to_csv('data/target_map.csv', index=False)