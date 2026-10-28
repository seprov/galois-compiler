#!/usr/bin/env python

import sys

NODES_X=int(sys.argv[1])
NODES_Y=int(sys.argv[2])

total_nodes = NODES_X * NODES_Y
total_edges = (NODES_X - 1) * NODES_Y + (NODES_Y - 1) * (NODES_X * 1)

print("p %d %d" % (total_nodes, total_edges))

#print "digraph {"
lasty = 0
for y in range(NODES_Y):
    lastx = NODES_X * y
    for x in range(NODES_X * y, NODES_X * (y+1)):
        #print x, ";"
        if x > lastx:
            #print "%d -> %d;" % (lastx, x)
            print("a %d %d %d" % (lastx+1, x+1, 1))

        lastx = x

        if y > lasty:
            #print "%d -> %d" % (x - NODES_X, x)
            print("a %d %d %d" % (x - NODES_X+1, x+1, (y*NODES_X+x+y) % NODES_X + 2))

    lasty = y

#print "}"
