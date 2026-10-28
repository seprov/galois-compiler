#!/bin/bash

APPS="bfs-topo bfs-cx bfs-tp bfs-hybrid sssp-topo bfs-wl sssp-wl sssp-nf sssp-wl-noprio mis mst-wl mst-wl-test dmr pr-tp pr-residual pr-residual-wl cc triangles mis-checker"

if [ $# -lt 1 ]; then
    echo Usage: $0 revision
    exit 1;
fi;

REV=$1

if [ -d ggc ]; then
    echo Directory ggc already exists. Not cloning.
else
    echo "cloning"
    hg clone -r$REV ~/src/ggc || exit 1
fi;

cd ggc

[ -d inputs ] || ln -v -s ~/ws/inputs 
[ -d gensrc ] || mkdir -v gensrc

for a in $APPS; do
    if [ ! -d gensrc/$a ]; then
	mkdir -vp gensrc/$a
    fi;
done;

[ -d rt/include/mgpu ] || ln -v -s /h2/sreepai/pd/gunrock/externals/moderngpu rt/include/mgpu

[ -d rt/lib ] || mkdir -v rt/lib

cp ~/src/ggc/bmks/Makefile bmks/

echo "making rt, bmks"
make rt || exit 2

for a in $APPS; do
    if [ -d bmks/$a ] && [ -f bmks/$a/Makefile ]; then
	make -C bmks/$a || exit 3;
    fi;
done;

for a in $APPS; do
    if [ -d bmks/$a ]; then
	# prior to 250, we did not have Makefiles in gensrc?
	[ -f gensrc/$a/Makefile ] || { [ -f gensrc/$a/kernel.cu ] && ln -v -s ../../skelapp/SAMakefile gensrc/$a/Makefile ; } 
    else
	rmdir gensrc/$a
	continue;
    fi;

    [ -f gensrc/$a/bmktest2.py ] || { [ -f gensrc/$a/Makefile ] && ln -v -s ~/src/ggc/bmks/$a/bmktest2.py gensrc/$a/bmktest2.py ; }

done;

[ -f bmks/Makefile.gen ] || cp ~/src/ggc/bmks/Makefile.gen bmks/

echo "DONE"
