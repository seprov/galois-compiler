# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph
from gg.ast.params import GraphParam

import cgen

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
        Kernel("bfs_topo", [G.param(), ('int', 'LEVEL')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["if(graph.node_data[node] != (LEVEL - 1)) continue"]),
	                #CDecl(("bool", "pop", "")),
                        #CBlock(["pop = node < graph.nnodes && (graph.node_data[node] == (LEVEL - 1))"], parse=False),
                        ForAll("edge", G.edges("node"),
                               [
                                CDecl(("index_type", "dst", "= graph.getAbsDestination(edge)")),
                                If("graph.node_data[dst] == INF", 
                                    [CBlock(["graph.node_data[dst] = LEVEL"]),
                                     ReturnFromParallelFor("true")], [])
                                ]
                               )
                        ]
                       ),
                ]),        
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [Invoke("bfs_init", ("gg",'0')),
                CDecl(("int", "LEVEL", "= 1")),
                ClosureHint(Iterate("while", "any", "bfs_topo", ('gg','LEVEL'), 
                                    stmts = [CBlock(["LEVEL++"])],
                                )
                        ),
            ]
           )
]
)
             
