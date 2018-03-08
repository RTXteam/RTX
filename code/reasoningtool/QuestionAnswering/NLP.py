import nltk
sentence = "What proteins does carbetocin target"
tokens = nltk.word_tokenize(sentence)
grammar1 = nltk.CFG.fromstring("""
  S -> NP VP
  VP -> V NP | V NP PP
  PP -> P NP
  V -> "interacts" | "targets" | "target"
  NP -> "protein" | "proteins" | "Bob" | Det N | Det N PP
  Det -> "a" | "an" | "the" | "my" | "What"
  N -> "carbetocin" | "dog" | "cat" | "telescope" | "park"
  P -> "does" | "on" | "by" | "with"
  """)
rd_parser = nltk.RecursiveDescentParser(grammar1)
rd_parser.parse(tokens)
# http://www.nltk.org/book/ch08.html