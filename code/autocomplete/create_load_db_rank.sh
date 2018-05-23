#remove previous db
rm dict.db;

#find max
# unigram max guaranteed to be larger than bigram max
MAX=$(($(head -n 1 data/unigrams.histogrammed.stripped.filtered | cut -d ' ' -f1) + 1))

#create temp file for nodes here
cat data/NodeNamesDescriptions.tsv | cut -f2 | sed "s/^/$MAX /g" | perl -pe 's/ /\t/' > nodeNames.tmp

#create temp file for questions here
cat data/Questions.tsv | cut -f2-3 | sed 's/$[a-z0-9]*//g' | sed 's/[^A-Z^a-z^0-9 \t,]//g' | sed 's/\t/,/g' | sed 's/ *, */\n/g' | sed "s/^/$MAX /g" | perl -pe 's/ /\t/' > questions.tmp

#create temp file for tabbed data
cat data/unigrams.histogrammed.stripped.filtered | perl -pe 's/ /\t/' > uni.tmp
cat data/bigrams.histogrammed.stripped.filtered | perl -pe 's/ /\t/' > bi.tmp

./sqlite3 dict.db <<< ".read create.sql"

#remove temp files here
rm nodeNames.tmp
rm questions.tmp
rm bi.tmp
rm uni.tmp
