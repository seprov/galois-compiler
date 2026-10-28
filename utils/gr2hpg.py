#!/usr/bin/env python
import graph
import sys
import os

grf = graph.CSRGraph()
gr = graph.GRGraphReader()
gr.read(sys.argv[1])
gr.populate_csr(grf)

f = sys.stdout

print(grf.num_nodes, file=f)
c = 0
for N in grf.nodes():
    print("%d %d" % (c, N.out_degree()), file=f)
    c += N.out_degree()

print("\n0\n", file=f)
print(grf.num_edges, file=f)
for E in grf.all_edges():
    print("%d %d" % (E[1], E[2]), file=f)
