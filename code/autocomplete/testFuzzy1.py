#!/env python3

import os
import sys
import timeit

import rtxcomplete

rtxcomplete.load()
limit = 20
word = "mala"
word = " insulin"
#word = "aceta"
#word = "acetam"
#word = "acetamino"
#word = "profe"
word = "profer"
#word = "malarials"
#word = "P0123"
#word = "ABCG"

t0 = timeit.default_timer()
result = rtxcomplete.get_nodes_like(word,limit)
t1 = timeit.default_timer()

print("======================")
if 1:
    for term in result:
        print(f" - {term['name']}")
else:
    print(result)

print(f"INFO: Information retrieved in {t1-t0} sec")
