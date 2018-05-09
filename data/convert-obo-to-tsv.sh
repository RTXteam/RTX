#!/bin/bash

# to be blamed for this script:  Stephen Ramsey

rep -v 'alt_id\:' go.obo | \
    egrep 'namespace\:|id\:|name\:' | \
    /usr/local/bin/gtr --delete "\n" | \
    /usr/local/bin/sed 's/name\:/\t/g' | \
    /usr/local/bin/sed 's/id\:/\n/g' | \
    /usr/local/bin/sed 's/namespace\:/\t/g' > go.tsv
