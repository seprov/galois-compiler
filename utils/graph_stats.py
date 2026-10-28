#!/usr/bin/env python
import graph
import sys
from statlib import stats

grf = graph.CSRGraph()
gr = graph.GRGraphReader()
gr.read(sys.argv[1])
gr.populate_csr(grf)

degree = []
for N in grf.nodes():
    degree.append(N.out_degree())

print "max_degree: %d" % max(degree)
print "mode: ", stats.mode(degree)
#print "median: ", stats.median(degree)
print "item freq:\n", "\n".join(["%s %s" % (v, f) for v, f in stats.itemfreq(degree)])
