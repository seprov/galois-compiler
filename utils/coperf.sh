#!/bin/bash

P=`dirname $0`
if [ $# -ne 2 ]; then
    echo Usage: $0 rev perf-output
    exit 1;
fi;

REV=$1
OF=$2

[ -f $OF ] && { echo "$OF exists, not running" ;  exit 0; }

if $P/corun.sh $REV; then
    for f in ggc/gensrc/*; do
	if [ -d $f ] && [ -f $f/Makefile ] && [ "$f" != "ggc/gensrc/skelapp" ]; then
	    make -C $f || exit 3
	fi;
    done;

    ~/src/bmk2/test2.py -d ~/irglcmp2 --scan ggc/gensrc --log $OF -v perf
    #~/src/bmk2/test2.py -d ~/irglcmp2 --scan ggc/gensrc --log $OF --bispec quick -v perf
else
    exit 2
fi;

exit 0
