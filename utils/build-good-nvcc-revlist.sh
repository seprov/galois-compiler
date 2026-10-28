#!/bin/bash

P=`dirname $0`
F=$P/known-good-ggc-revisions.txt
O=$P/known-good-nvcc-revisions.txt

touch $O

tac $F | while read REV STATUS; do
    if [ $STATUS -eq 0 ]; then
	
	grep "^$REV " $O && continue;
	
	$P/cobuild.sh $REV
	RET=$?	
	echo "$REV $RET" >> $O
	rm -rf ggc
    fi;
done;
