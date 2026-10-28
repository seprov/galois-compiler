#!/bin/bash

P=`dirname $0`
LLGGC=$P/../src/llggc.py

for i in "$@"; do
    $LLGGC --dump-ast "$i"
done;
