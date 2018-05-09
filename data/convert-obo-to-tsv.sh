#!/bin/bash

# to be blamed for this script:  Stephen Ramsey

egrep -v 'def\:|synonym\:|alt_id\:|is_a\:|comment\:' go.obo | \
    egrep 'namespace\:|id\:|name\:' | \
    /usr/local/bin/gtr --delete "\n" | \
    /usr/local/bin/sed 's/name\: /\t/g' | \
    /usr/local/bin/sed 's/id\: /\n/g' | \
    /usr/local/bin/sed 's/namespace\: /\t/g' | \
    grep 'GO:' | \
    awk -F"\t" '{print $3 "\t" $1 "\t" $2 "\tgeneric" }' > go.tsv

