#!/bin/bash

# converts a Galois GR file to triangles file via DIMACS


T=`mktemp`

for IF in "$@"; do
    echo $IF

    F=`basename "$IF" .gr`
    O1="$F.tri.bin"
    O2="$F.tri.gr"

    if [ -f "$IF" ]; then
	if [ -f "$O1" ]; then
	    echo "$O1 exists! Not converting."
	else	
	    ~/graph-convert -gr2dimacs "$IF" $T && ~/irglcmp/triangles/convert-from-dimacs-main.e $T "$O1"
	fi;

	if [ -f "$O2" ]; then
	    echo "$O2 exists! Not converting."
	else
	    ~/irglcmp/triangles/convert-to-dimacs-main.e "$O1" $T && ~/graph-convert -dimacs2gr $T "$O2"
	fi;
    fi;
done;

rm -v "$T"
