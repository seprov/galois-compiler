#!/bin/bash

OUT=""
for i in "$@"; do
    x=`mktemp --tmpdir tmpXXXXX.png`
    dot -Tpng "$i" -o $x
    OUT="$OUT $x"
    eog $x &
done;
wait
rm -v $OUT
