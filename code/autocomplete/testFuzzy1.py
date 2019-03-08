#!/env python3

import os
import sys
import rtxcomplete

rtxcomplete.load()
limit = 10
word = "mala"
#word = "P0123"
result = rtxcomplete.get_nodes_like(word,limit)
print(result)

