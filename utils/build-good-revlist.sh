#!/bin/bash

P=`dirname $0`
F=$P/known-good-ggc-revisions.txt
touch $F

for((i = 553; i>0;i--)); do
    if grep "^$i " $F; then
	continue;
    else
	~/src/ggc/utils/corun.sh $i
	echo "$i $?" >> $F
	rm -rf ggc
    fi;
done;
