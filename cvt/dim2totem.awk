#!/usr/bin/gawk -f

/^p sp/ { printf "#Nodes:%s\n#Edges:%s\n#Directed\n", $3, $4}
/^a/ {print $2-1, $3-1, $4}
