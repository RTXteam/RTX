#remove previous db
rm dict.db;

#create temp file for nodes here
cat ../../data/autocomplete/NodeNamesDescriptions.tsv | cut -f2 > nodeNames.tmp

#create temp file for questions here
cat ../../data/autocomplete/Questions.tsv | cut -f2-3 | sed 's/$[a-z0-9]*//g' | sed 's/[^A-Z^a-z^0-9 \t,]//g' | sed 's/\t/,/g' | sed 's/ *, */\n/g' > questions.tmp

./sqlite3 dict.db <<< ".read create.sql"

#remove temp files here
rm nodeNames.tmp
rm questions.tmp
