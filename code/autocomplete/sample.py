"""
Example External App that uses rtxcomplete
"""

import rtxcomplete

def test_prefix():
  completions = rtxcomplete.prefix("NF", 10)
  print completions
  # add assertion here

def test_fuzzy():
  matches = rtxcomplete.fuzzy("NF", 10)
  print matches
  # add assertion here
  
if rtxcomplete.load():
  test_prefix()
  test_fuzzy()
