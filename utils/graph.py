#!/usr/bin/env python

import struct
import time
import gc

CHATTY = True
CHATTY_LEVEL = 1
if CHATTY:
    import sys

class Kernel(object):
    pass

class Node(object):
    def __init__(self, n):
        self.n = n
        self.edges_d = []

    def add_edge(self, edge):
        self.edges_d.append(edge)

    def edges(self):
        return self.edges_d

    def get_edge(self, i):
        return self.edges_d[i]

    def out_degree(self):
        return len(self.edges_d)

    def in_degree(self):
        return self.indegree

class Edge(object):
    def __init__(self, src, dst, weight, data = None):
        self.src_d = src
        self.dst_d = dst
        self.weight_d = weight
        self.data_d = data

    def dest(self):
        return self.dst_d

    def src(self):
        return self.src_d

    def data(self):
        return self.data_d

    def weight(self):
        return self.weight_d

    def __str__(self):
        return "%s -> %s weight %d" % (self.src_d.n, self.dst_d.n, self.weight_d)

class Graph(object):
    def __init__(self, NodeType = Node, EdgeType = Edge):
        self.node_type = NodeType
        self.edge_type = EdgeType
        self.nodes_d = []

    def set_size(self, num_nodes, num_edges):
        self.num_nodes = num_nodes
        self.num_edges = num_edges
        
    def add_node(self, node):
        self.nodes_d.append(node)

    def nodes(self):
        return self.nodes_d

    def get_node(self, i):
        return self.nodes_d[i]

    def all_edges(self):
        for N in self.nodes():
            for e in N.edges():
                yield e

    def display(self):
        for e in self.all_edges():
            print e

class CSRNode(Node):
    def __init__(self, n, csrg):
        self.n = n
        self.csrg = csrg

    def add_edge(self, e):
        pass

    def out_degree(self):
        offset = self.csrg.offsets[self.n]
        last_offset = self.csrg.offsets[self.n - 1] if self.n > 0 else 0

        return offset - last_offset

    def get_edge(self, i):
        offset = self.csrg.offsets[self.n - 1] if self.n > 0 else 0
        next_offset = self.csrg.offsets[self.n]

        if i < 0 or i >= (next_offset - offset):
            raise IndexError

        return (self.n, self.csrg.edges[offset + i], self.csrg.edge_data[offset])

    def edges(self):
        offset = self.csrg.offsets[self.n]
        last_offset = self.csrg.offsets[self.n - 1] if self.n > 0 else 0
        
        for dst, data in zip(self.csrg.edges[last_offset:offset], self.csrg.edge_data[last_offset:offset]):
            yield (self.n, dst, data)

class CSRGraph(Graph):
    def __init__(self, NodeType = CSRNode, EdgeType = Edge):
        # but note the custom types are completely ignored
        super(CSRGraph, self).__init__(NodeType, EdgeType)

    def add_node(self):
        pass
    

    def get_node(self, i):
        if i < 0 or i >= self.num_nodes:
            raise IndexError
        
        N = self.node_type(i, self)
        if hasattr(self, 'indegree'):
            N.indegree = self.indegree[i]
        
        return N

    def nodes(self):
        for i in range(self.num_nodes):
            N = self.node_type(i, self)
            if hasattr(self, 'indegree'):
                N.indegree = self.indegree[i]

            yield N

    def calc_indegree(self):
        self.indegree = [0] * self.num_nodes

        for i in self.edges:
            self.indegree[i] += 1

    def all_edges(self):
        last_offset = 0
        for src, offset in enumerate(self.offsets):
            degree = offset - last_offset
            
            if degree > 0:
                for dst, data in zip(self.edges[last_offset:offset], self.edge_data[last_offset:offset]):
                    yield (src, dst, data)

            last_offset = offset

class GRGraphReader(object):
    def populate_csr(self, grf):
        grf.set_size(self.num_nodes, self.num_edges)

        grf.offsets = self.offsets
        grf.edges = self.edges
        grf.edge_data = self.edge_data

    def populate(self, grf):
        grf.set_size(self.num_nodes, self.num_edges)

        t_st, t_end = 0, 0
        
        t_st = time.clock()
        nodes = []
        for i in range(self.num_nodes):
            nodes.append(grf.node_type(i))
        t_end = time.clock()

        if CHATTY:
            print >>sys.stderr, "Creating nodes: ", t_end - t_st

        t_st = time.clock()
        last_offset = 0
        gt = grf.edge_type
        y = 0
        
        eit = iter(self.edges)
        edit = iter(self.edge_data)
        Nedges = 0

        gc.disable()

        for src, offset in enumerate(self.offsets):
            degree = offset - last_offset
            Nedges += degree
            if CHATTY and CHATTY_LEVEL > 1: print >>sys.stderr, degree, Nedges   

            N = nodes[src]

            N.edges_d = [None] * degree
            i = 0
            while degree > 0:
                N.edges_d[i] = gt(nodes[src], nodes[next(eit)], next(edit))
                degree -= 1
                i += 1

            grf.add_node(N)

            last_offset = offset

        t_end = time.clock()
        if CHATTY: print >>sys.stderr, "Creating edges: ", t_end - t_st, Nedges
        #gc.enable()

    def _read_array_from_file_2(self, ty, n, f):
        """Read N items of type ty (struct.Struct) into a array"""

        # could've used array except it doesn't support 64-bit types until 3.3
        st = time.clock()
        sz = ty.size
        out = []
        for i in range(n):
            d = f.read(sz)
            out.append(ty.unpack(d)[0])

        end = time.clock()
        print "total", end - st

        return out

    # only handles very simple types
    def _primitive_type(self, pt):
        bsa = ''
        repeat = 1
        ty = pt[-1]
        
        if len(pt) >= 3:
            bsa = pt[0]
            repeat = int(pt[1:-1])
        elif len(pt) == 2:
            bsa = pt[0]
            if bsa not in ('@', '=', '<', '>', '!'):
                repeat = int(bsa)
            else:
                repeat = 1

        return (bsa, repeat, ty)

    def _read_array_from_file(self, ty, n, f):
        """Read N items of type ty (struct.Struct) into a array"""
        per_round = 128

        oldty = self._primitive_type(ty.format)
        nty = struct.Struct("%s%d%s" % (oldty[0], oldty[1] * per_round, oldty[2]))

        #st = time.clock()
        sz = ty.size * per_round

        assert nty.size == sz

        out = []
        for i in range(n/per_round):
            d = f.read(sz)
            out += list(nty.unpack(d))

        for i in range(n % per_round):
            d = f.read(ty.size)
            assert len(d) != 0
            out += list(ty.unpack(d))

        #end = time.clock()
        #print "total", end - st

        return out

    def read(self, f):
        g = open(f, "r")
        t_st = time.clock()
 	# uint64_t* fptr = (uint64_t*)m;
  	# __attribute__((unused)) uint64_t version = le64toh(*fptr++);
  	# assert(version == 1);
  	# uint64_t sizeEdgeTy = le64toh(*fptr++);
  	# uint64_t numNodes = le64toh(*fptr++);
  	# uint64_t numEdges = le64toh(*fptr++);
  
        fmt = '<4Q'
        sz = struct.calcsize(fmt)
        header = g.read(sz)
        version, sizeEdgeTy, numNodes, numEdges = struct.unpack(fmt, header)
        assert(version == 1)

        if CHATTY: print >>sys.stderr, "reading %s: %d nodes, %d edges" % (f, numNodes, numEdges)

        self.num_nodes = numNodes
        self.num_edges = numEdges
        self.offsets = self._read_array_from_file(struct.Struct('<Q'), numNodes, g)

  	# uint64_t *outIdx = fptr;
  	# fptr += numNodes;

        self.edges = self._read_array_from_file(struct.Struct('<L'), numEdges, g)

        # if (numEdges % 2) fptr32 += 1;
        if numEdges % 2:
            g.read(struct.Struct('<L').size)

        assert sizeEdgeTy == 4

        self.edge_data = self._read_array_from_file(struct.Struct('I'), numEdges, g)
        
        g.close()
        t_end = time.clock()

        if CHATTY: print >>sys.stderr, "reading done.", t_end - t_st


if __name__ == "__main__":
    import sys
    grf = Graph()
    gr = GRGraphReader()
    gr.read(sys.argv[1])
    gr.populate(grf)

    all_e = grf.all_edges()
    for N in grf.nodes():
        for e in N.edges():
            print e, next(all_e)
        
        print

