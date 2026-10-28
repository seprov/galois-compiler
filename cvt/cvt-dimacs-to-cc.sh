#!/bin/bash

# converts a DIMACS file to .edges.txt and .parameters.txt file as input to CC

for IF in "$@"; do
    echo $IF

    F=`basename "$IF" .dimacs`
    FF=`dirname "$IF"`/$F
    O1="$FF.edges.txt"
    O2="$FF.parameters.txt"

    if [ -f "$IF" ]; then
	if [ -f "$O1" ] || [ -f "$O2" ]; then
	    echo "$O1 or $O1 exists! Not converting."
	else	
	    awk -v edges=$O1 -v parameters=$O2  '/p sp/ {print $4, $3 > parameters;}  /^a/ {print $2, $3 > edges}' "${FF}.dimacs"
	fi;
    fi;
done;
