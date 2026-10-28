#!/bin/bash

P=`dirname $0`
BMKS=$P/../bmks

for i in `make --no-print-directory -C $BMKS list-apps`; do
    make -C $i backup
done
