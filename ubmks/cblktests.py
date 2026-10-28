# -*- mode: python -*-

from gg.ast import *

import cgen
ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                cgen.Define("INF", 10000)]),

        Kernel("kernel", [('CSRGraph', 'graph'), ('int', 'src'), ('int *', 'a')],
               [CDecl([('int', 'node', ''),
                       ('int', 'tmp', ''),
                       ('int*', 'y', ''),
                       ('int*', 'c', ''),
                       ('int*', 'b', ''),
                       ('int*', 'l', ''),
                       ('int', 'j', '= graph.getAbsoluteEdge(tmp)'),
                       ('int', 'i', ''),
                       ('int*', 'x', ''),
                       ('int*', 'z', ''),]),
                CBlock(["a[x+y+z] = 1"]),
                CBlock(["graph.node_data[node] = (node == src) ? 0 : INF "]),
                CBlock(["tmp = a = *y * b"]),
                CBlock(["a[c[i]] = b[j]"]),
                CBlock(["a[c[i]] = l[j]"]),
                CBlock(["graph->x = x.y"]),
                CBlock(["j = y + i++"]),
                CBlock(["a = x + ++i"]),
                CBlock(["++i = 2"])
                ]
               ),

        Kernel("kernel2", [('CSRGraph', 'graph'), ('int', 'LEVEL')],
               [
                CDecl([("index_type", "dst", ""), ("int", "edge", "")]),
                CBlock(["dst = graph.edge_dst[edge]"]),
                CBlock(["graph.node_data[dst] = LEVEL++"]),
                ]
               ),

        Kernel("gg_main", [('CSRGraph&', 'hg'), ('CSRGraph&', 'gg')], 
               [CDecl(("int", "LEVEL", "= 1")),
                CBlock(["LEVEL++"])]
               )
        ])
