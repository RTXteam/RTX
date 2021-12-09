#!/usr/bin/python3
import json
import requests
import timeit

dir = '/mnt/data/orangeboard/Cache/callbacks'

counter = 6
done = False

while not done:
    filename = f"{counter:05}.json"
    print(filename)

    with open(filename) as infile:
        response = json.load(infile)
    print(response['submitter'])

    counter += 1
    if counter > 21:
        break







