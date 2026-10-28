#!/bin/bash

cd bmks
../tests/compile_all.sh
echo ""
echo "*** Compiling ubmks"
make -C ../ubmks
