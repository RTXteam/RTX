#!/usr/bin/python3
import json
import requests
import timeit
import os

dir = '/mnt/data/orangeboard/Cache/callbacks'

counter = 6
done = False

results = {}
queries = {}
states = {}

while not done:
    filename = f"{counter:05}.json"
    filepath = f"{dir}/{filename}"

    #print(filename)

    if not os.path.exists(filepath):
        break

    with open(filepath) as infile:
        response = json.load(infile)

    submitter = response['submitter']
    response_id = response['id']
    response_id = response_id.replace('api/arax/v1.2/response/','?r=')

    components = submitter.split('_')
    state = components[0]
    query = components[1]
    query = query.replace('.json','')
    n_results = len(response['message']['results'])
    try:
        essence = response['message']['results'][0]['essence']
    except:
        essence = ''

    queries[query] = 1
    states[state] = 1

    if state not in results:
        results[state] = {}
    results[state][query] = { 'response_id': response_id, 'n_results': n_results, 'essence': essence }

    print(f"{state}\t{query}\t{response_id}")

    counter += 1
    if counter > 121:
        break

sorted_queries = sorted(queries.keys())

print('Query\tBefore\tAfter')
print('-----\t------\t-----')
for query in sorted_queries:
    try:
        before_n_results = str(results['before'][query]['n_results'])
        before_essence = str(results['before'][query]['essence'])
        before_response_id = str(results['before'][query]['response_id'])
    except:
        before_n_results = ''
        before_n_results = ''
        before_response_id = ''
    try:
        after_n_results = str(results['after'][query]['n_results'])
        after_essence = str(results['after'][query]['essence'])
        after_response_id = str(results['after'][query]['response_id'])
    except:
        after_n_results = ''
        after_n_results = ''
        after_response_id = ''

    print(f"{query}\t{before_n_results}\t{after_n_results}\t{before_response_id}\t{after_response_id}")





