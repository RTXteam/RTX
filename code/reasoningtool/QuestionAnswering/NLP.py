import nltk
sentence = "Mary saw Bob"
tokens = nltk.word_tokenize(sentence)
grammar1 = nltk.CFG.fromstring("""
  S -> NP VP
  VP -> V NP | V NP PP
  PP -> P NP
  V -> "saw" | "ate" | "walked"
  NP -> "John" | "Mary" | "Bob" | Det N | Det N PP
  Det -> "a" | "an" | "the" | "my"
  N -> "man" | "dog" | "cat" | "telescope" | "park"
  P -> "in" | "on" | "by" | "with"
  """)
rd_parser = nltk.RecursiveDescentParser(grammar1)
rd_parser.parse(tokens)
for tree in rd_parser.parse(tokens):
	print(tree)
# http://www.nltk.org/book/ch08.html
# demo.ark.cs.cmu.edu/parse



