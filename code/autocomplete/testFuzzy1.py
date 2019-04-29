#!/env python3

import os
import sys
import rtxcomplete

rtxcomplete.load()
limit = 50
word = "mala"
#word = " insulin"
word = "aceta"
word = "acetam"
word = "acetami"
word = "profe"
word = "malat"
#word = "P0123"

result = rtxcomplete.get_nodes_like(word,limit)

if 1:
  for word in result:
    print(word["name"])
else:
  print(result)

