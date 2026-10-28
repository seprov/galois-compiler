#!/usr/bin/gawk -f

/^p sp/ { print $3, $4 }
/^a/ {print $2-1, $3-1, $4}
