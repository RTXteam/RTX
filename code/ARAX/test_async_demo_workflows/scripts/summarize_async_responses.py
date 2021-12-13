#!/usr/bin/python3
import json
import requests
import timeit
import os
import argparse

dir = '/mnt/data/orangeboard/Cache/callbacks'

argparser = argparse.ArgumentParser(
    description='Summarize the results of a series of callbacks')
argparser.add_argument('--starting_callback_number', action='store', type=int,
                        help='The first callback number to process')
argparser.add_argument('--ending_callback_number', action='store', type=int,
                        help='The last callback number to process')

args = argparser.parse_args()

if not args.starting_callback_number or not args.ending_callback_number:
    print("ERROR: Must supply both --starting_callback_number and --ending_callback_number")
    print("       See --help for more information")
    exit()

counter = args.starting_callback_number
done = False

results = {}
queries = {}
states = {}

while counter <= args.ending_callback_number:
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

print('Query\t' + "\t".join(states))
print('-------------------------------------------------------')
for query in sorted_queries:
    n_results_list = []
    response_id_list = []

    for state in states:
        try:
            n_results = str(results[state][query]['n_results'])
            essence = str(results[state][query]['essence'])
            response_id = str(results[state][query]['response_id'])
        except:
            n_results = ''
            n_results = ''
            response_id = ''

        n_results_list.append(n_results)
        response_id_list.append(response_id)

    print(f"{query}\t" + "\t".join(n_results_list) + "\t" + "\t".join(response_id_list))





