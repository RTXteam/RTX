#!/env python3

import os
import sys
import rtxcomplete

rtxcomplete.load()
limit = 10
word = "mala"
result = rtxcomplete.fuzzy2(word,limit)
print(result)

