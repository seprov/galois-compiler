# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.ast.params import GraphParam
import cgen

WL = Worklist()
G = Graph("graph")

ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                ]),
        CDeclGlobal(("extern const node_data_type", "INF", "= INT_MAX")),
        Kernel("bfs_init", [G.param(), ('int', 'src')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["graph.node_data[node] = (node == src) ? 0 : INF "])]
                       )
                ]
               ),

        Kernel("bfs_kernel", [G.param(), ('int', 'LEVEL')],
               [ForAll("wlnode", WL.items(), 
                       [CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode", "node"), 
                        ForAll("edge", G.edges("node"),
                               [                                
                                CDecl(("index_type", "dst", "")),
                                CBlock(["dst = graph.getAbsDestination(edge)"]),
                                If("graph.node_data[dst] == INF",
                                   [CBlock(["graph.node_data[dst] = LEVEL"]),
                                    WL.push("dst")], []),
                                WL.push("dst",_coop_only=True)
                                ]
                           )
                        ]
                       ),
                #GlobalBarrier().sync()
                ]
               ),
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [Invoke("bfs_init", ("gg",'0')),
                CDecl(("int", "LEVEL", "= 1")),
                ClosureHint(Iterate("while", "wl", "bfs_kernel", ('gg','LEVEL'), 
                                    WLInit("gg.nnodes", [0]), 
                                    stmts = [CBlock(["LEVEL++"])],
                                ),
                        )
            ]
           )
])
