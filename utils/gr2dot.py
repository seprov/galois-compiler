#!/usr/bin/env python
import graph
import sys
import os
import tempfile

grf = graph.CSRGraph()
gr = graph.GRGraphReader()
gr.read(sys.argv[1])
gr.populate_csr(grf)

tmpfile = tempfile.NamedTemporaryFile(suffix=".dot", delete=False)

print("digraph {", file=tmpfile)
for N in grf.nodes():
    #if N.n >= 1:
    #    break

    print("%d;" % (N.n,), file=tmpfile)
    
    for e in N.edges():
        print('%d -> %d [label="%d"]' % (e[0], e[1], e[2]), file=tmpfile)


print("}", file=tmpfile)
tmpfile.close()

tmpfile2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
tmpfile2.close()

os.system("dot -Tpng -o %s %s && eog %s" % (tmpfile2.name, tmpfile.name, tmpfile2.name))
