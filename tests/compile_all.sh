#!/bin/bash


P=`dirname $0`
SRC=$P/../bmks/
GENSRC=$P/../gensrc
UTILS=$P/../utils
all=`make -sC $P/../bmks/ list-apps`
X=$#

echo ""
echo "*** Running high-level compiler"

pushd $SRC
for i in $all; do
    pushd $i && make -B && popd || exit
done;

echo ""
echo "*** Running native compiler"
pushd $GENSRC
for i in $all; do
    pushd $i && make && popd || exit
done;

if [ $X -lt 2 ]; then
    echo "" $X    
    echo "*** Executing tests"
    for i in $all; do
	pushd $i && ../$UTILS/runtests && popd
    done
fi;

popd 
popd
