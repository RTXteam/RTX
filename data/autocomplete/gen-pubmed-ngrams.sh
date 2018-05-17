# Generate Unigrams and Bigrams From pubmed

# DO THIS BEFORE RUNNING: generate data from medline files
# download source data from ftp://ftp.ncbi.nlm.nih.gov/pubmed/baseline , in the form of medline*.gz and put in "abstracts" directory

# DO THIS BEFORE RUNNING: install xmlstarlet

# take each abstract from the pubmed files, normalize it and
# generate a newline terminated list of unigrams
for file in abstracts/*.gz
  do
    cat $file |
      xmlstarlet sel -t -v "//AbstractText" |
      tr [A-Z] [a-z] |
      tr -c [a-z0-9\-] ' ' |
      perl -pe "s/[ ]+/ /gi" |
      tr ' ' '\n'
  done > unigram-stream
  
# generate a newline file
printf "\n" > newline

# generate bigram-stream using paste
cat newline unigram-stream  | paste -d" " - unigram-stream > bigram-stream

sort unigram-stream | uniq -c | sort -nr > unigrams.sorted
sort bigram-stream | uniq -c | sort -nr > bigrams.sorted

