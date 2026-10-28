#!/usr/bin/gawk -f

BEGIN {print "%%MatrixMarket matrix coordinate integer general"}
/^p sp/ { print $3, $3, $4 }
/^a/ {print $2, $3, $4}
