#!/bin/bash

P=`dirname $0`
if [ $# -ne 1 ]; then
    echo Usage: $0 rev
    exit 1;
fi;

REV=$1

if $P/corun.sh $REV; then
    for f in ggc/gensrc/*; do
	if [ -d $f ] && [ -f $f/Makefile ] && [ "$f" != "ggc/gensrc/skelapp" ]; then
	    make -C $f || exit 3
	fi;
    done;
else
    exit 2
fi;

exit 0
