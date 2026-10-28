# -*- mode: python -*-

from gg.ast import *
from gg.ast.anno import *
from gg.lib.wl import Worklist
from gg.lib.graph import Graph

import cgen

G = Graph("graph")
WL = Worklist()

ast = Module([
        CBlock([cgen.Define("INF", 10000000)]),
        Kernel("kernel2", [('CSRGraph', 'graph'), ('int', 'LEVEL')],
               [Uniform(ForAll("wlnode", WL.items(), 
                       [CDecl([("bool", "pop", ""),
                               ("int", "node", "")]),
                        WL.pop("pop", "wlnode", "node"), 
                        Uniform(ForAll("edge", G.edges("node"),
                               [                                
                                CDecl(("index_type", "dst", "")),
                                CBlock(["dst = graph.edge_dst[edge]"]),
                                If("graph.node_data[dst] == INF",
                                   [CBlock(["graph.node_data[dst] = LEVEL"]),
                                    WL.push("dst")], [])
                                ]
                               ))
                        ]
                       )
                        ),
                ]),
        ])
