#!/usr/bin/env python
import graph
import sys
import os

grf = graph.CSRGraph()
gr = graph.GRGraphReader()
gr.read(sys.argv[1])
gr.populate_csr(grf)

f = sys.stdout

print >>f, grf.num_nodes
c = 0
for N in grf.nodes():
    print >>f, "%d %d" % (c, N.out_degree())
    c += N.out_degree()

print >>f, "\n0\n"
print >>f, grf.num_edges
for E in grf.all_edges():
    print >>f, "%d %d" % (E[1], E[2])
