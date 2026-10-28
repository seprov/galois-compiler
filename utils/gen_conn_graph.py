#!/usr/bin/env python

import sys
import math
import random

class Output(object):
    def start(self, nnodes, nedges):
        pass

    def stop(self):
        pass

    def edge(self, s, d):
        pass

def prefix_sum(array):
    out = [0] * len(array)
    s = 0
    for i, v in enumerate(array):
        out[i] = s
        s += v

    out.append(s)
    return out

class DOTOutput(object):
    def start(self, nnodes, nedges):
        print "digraph {"
        print "# nnodes = %d" % (nnodes,)
        print "# nedges = %d" % (nedges,)

        print >>sys.stderr, "nnodes = %d" % (nnodes,)
        print >>sys.stderr, "nedges = %d" % (nedges,)

    def stop(self):
        print "}"

    def edge(self, s, d):
        print "%d -> %d;" % (s, d)

class DIMACSOutput(object):
    def start(self, nnodes, nedges):
        self.nnodes = nnodes
        self.nedges = nedges
        self.nedges_output = 0

        print >>sys.stderr, "nnodes = %d" % (nnodes,)
        print >>sys.stderr, "nedges = %d" % (nedges,)

        print "p sp %d %d" %  (self.nnodes, self.nedges)

    def edge(self, s, d, w = 1):
        print "a %d %d %d" % (s+1, d+1, w) # 1-based offset
        self.nedges_output += 1

    def stop(self):
        assert self.nedges == self.nedges_output

O = DIMACSOutput()
#O = DOTOutput()

#,], [33, 5, 33] + [257] + [1,]*29]

if len(sys.argv) < 2:
    print >>sys.stderr, "Usage: %0 d1,d2,d3:d4,d5" % (sys.argv[0],)
    sys.exit(0)

connectivity = [map(int, s.split(",")) for s in sys.argv[1].split(":")] 
print >>sys.stderr, "Parsed connectivity", connectivity

cnect = [sum(level) == len(level_next) for level, level_next in zip(connectivity, connectivity[1:])]
if not all(cnect):
    print >>sys.stderr, cnect
    sys.exit(0)

NNODES = sum([len(ln) for ln in connectivity]) + sum(connectivity[-1])
NEDGES = sum([sum(ln) for ln in connectivity])

level_node_0 = 0
level_next_node_0 = 0
O.start(NNODES, NEDGES)
for level, edges_per_node in enumerate(connectivity):
    level_next_node_0 += len(edges_per_node)
    s = 0
    for node_offset, edges in enumerate(edges_per_node):
        for e in range(edges):
            O.edge(level_node_0 + node_offset, level_next_node_0 + e + s, random.randint(1, 16))
        s += edges
    
    level_node_0 += len(edges_per_node)
    
O.stop()
