import sys
import math

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
        print("digraph {")
        print("# nnodes = %d" % (n,))
        print("# nedges = %d" % (n,))

        print("nnodes = %d" % (nnodes,), file=sys.stderr)
        print("nedges = %d" % (nedges,), file=sys.stderr)

    def stop(self):
        print("}")

    def edge(self, s, d):
        print("%d -> %d;" % (s, d))

class DIMACSOutput(object):
    def start(self, nnodes, nedges):
        self.nnodes = nnodes
        self.nedges = nedges
        self.nedges_output = 0

        print("nnodes = %d" % (nnodes,), file=sys.stderr)
        print("nedges = %d" % (nedges,), file=sys.stderr)

        print("p sp %d %d" %  (self.nnodes, self.nedges))

    def edge(self, s, d):
        print("a %d %d %d" % (s+1, d+1, 1)) # 1-based offset
        self.nedges_output += 1

    def stop(self):
        assert self.nedges == self.nedges_output

O = DIMACSOutput()

FANOUT = 32
TOTAL = 1024*1024*1024
LL = int(math.log(TOTAL, FANOUT))

NNODES = [FANOUT ** x for x in range(0, LL)]
NODE_START = prefix_sum(NNODES)
NEDGES = [n * FANOUT for n in NNODES[:-1]]

#print NNODES, sum(NNODES)
#print NEDGES, sum(NEDGES)
#sys.exit(1)
O.start(sum(NNODES), sum(NEDGES))

for level  in range(0, LL - 1):
    cur_level = NODE_START[level]
    next_level = NODE_START[level + 1]

    k = next_level

    for n in range(cur_level, next_level):
        for d in range(0, FANOUT):
            O.edge(n, k)
            k += 1
    
O.stop()
