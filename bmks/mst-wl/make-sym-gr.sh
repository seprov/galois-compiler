#!/bin/bash

if [ $# -lt 1 ]; then
	echo Usage: $0 file.dimacs
	exit 1;
fi;

I=$1
O="`basename $1 .dimacs`.gr"
OS="`basename $1 .dimacs`.sym.gr"

echo "Converting $I to $O and $OS"
GC=~/src/GaloisCpp/trunk/default/tools/graph-convert/graph-convert
$GC --dimacs2gr $I $O && $GC --gr2sintgr $O $OS
