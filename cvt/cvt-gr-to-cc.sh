#!/bin/bash

# converts a Galois GR file to .edges.txt and .parameters.txt file via
# DIMACS for input to CC


T=`mktemp`

for IF in "$@"; do
    echo $IF

    F=`basename "$IF" .gr`
    FF=`dirname "$IF"`/$F
    O1="$F.edges.txt"
    O2="$F.parameters.txt"

    if [ -f "$IF" ]; then
	if [ -f "$O1" ] || [ -f "$O2" ]; then
	    echo "$O1 or $O1 exists! Not converting."
	else	
	    if [ -f "${FF}.dimacs" ]; then
		echo "Using already existing dimacs file ${FF}.dimacs"
		awk -v edges=$O1 -v parameters=$O2  '/p sp/ {print $4, $3 > parameters;}  /^a/ {print $2, $3 > edges}' "${FF}.dimacs"
	    else
		~/graph-convert -gr2dimacs "$IF" $T && awk -v edges=$O1 -v parameters=$O2 '/p sp/ {print $4, $3 > parameters;}  /^a/ {print $2, $3 > edges}' $T
	    fi;
	fi;
    fi;
done;

rm -v "$T"
