#!/usr/bin/env python
import graph
import sys
import os

grf = graph.CSRGraph()
gr = graph.GRGraphReader()
gr.read(sys.argv[1])
gr.populate_csr(grf)

if len(sys.argv) > 2:
    fmt = sys.argv[2]
else:
    fmt = "PMA"

bitlimit = False

if fmt == "DIMACS-HPG":
    bitlimit = True
    fmt = "DIMACS"

if fmt == "HPG":
    bitlimit = True

output = dict([(i, set()) for i in range(grf.num_nodes)])
weights = dict()

# symmetrify
for E in grf.all_edges():    
    s, d, w = E
    output[s].add(d)
    output[d].add(s)

    if d == s:
        print("self loop")

    if (s, d) not in weights:
        if (d, s) not in weights:
            weights[(s, d)], weights[(d, s)] = w, w
        else:
            weights[(s, d)] = weights[(d, s)]        

# uniquify
W = 1
MAX_WEIGHT = 1023

for s in range(grf.num_nodes):
    for d in sorted(output[s]):
        if s <= d:
            weights[(s, d)], weights[(d, s)] = W, W
            W += 1
            
            if bitlimit:
                W = (W & MAX_WEIGHT)
                if W == 0: W = 1

num_edges = sum([len(output[k]) for k in output])

print("Writing %d nodes, %d edges" % (grf.num_nodes, num_edges), file=sys.stderr)

f = sys.stdout

if fmt == "PMA":
    print("writing PMA", file=sys.stderr) # file format for Sadegh Nobari's mst

    print(grf.num_nodes, num_edges, end=' ', file=f)

    for s in range(grf.num_nodes):
        assert len(output[s]) > 0
        for d in sorted(output[s]):
            print("%d %d" % (d, weights[(s, d)]), end=' ', file=f)

        print(file=f)
elif fmt == "DIMACS":
    print("writing dimacs (bitlimit=%s)" % (bitlimit,), file=sys.stderr) # for graphconvert to convert back to Galois GR
    print("p %d %d" % (grf.num_nodes, num_edges), file=f)

    for s in range(grf.num_nodes):
        assert len(output[s]) > 0
        for d in sorted(output[s]):
            print("a %d %d %d" % (s+1, d+1, weights[(s, d)]), file=f)
elif fmt == "HPG":
    print("writing HPG", file=sys.stderr) # for Pawan Harish/
    print(grf.num_nodes, file=f)
    c = 0
    for s in range(grf.num_nodes):
        print("%d %d" % (c, len(output[s])), file=f)
        c += len(output[s])

    print("\n0\n", file=f)
    print(num_edges, file=f)

    for s in range(grf.num_nodes):
        assert len(output[s]) > 0
        for d in sorted(output[s]):
            print("%d %d" % (d, weights[(s, d)]), file=f)
else:
    print("no idea what to write", file=sys.stderr)
