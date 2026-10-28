#!/bin/bash

P=`dirname $0`
F=$P/known-good-nvcc-revisions.txt

sort --random-sort $F | while read REV STATUS; do
    if [ $STATUS -eq 0 ]; then
	#OF=~/irgl-rev-perf-data/quick/logs/$REV.log
	OF=~/irgl-rev-perf-data/$REV.log
	CUDA_VISIBLE_DEVICES=2 $P/coperf.sh $REV $OF	
	rm -rf ggc
    fi;
done;
