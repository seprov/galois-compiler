# -*- mode: python -*-

from gg.ast import *
from gg.ast.params import GraphParam
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
import cgen

G = Graph("graph")
WL = Worklist()

ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                ]),
        CDeclGlobal(("extern const node_data_type", "INF", "= INT_MAX")),
        Kernel("sssp_init", [G.param(), ('int', 'src')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["graph.node_data[node] = (node == src) ? 0 : INF "])]
                       )
                ]
               ),
        Kernel("sssp_kernel", [G.param()],
               [ForAll("wlnode", WL.items(),                        
                       [CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode", "node"),
                        UniformConditional(If("pop && graph.node_data[node] == INF", [CBlock("continue")]), uniform_only = False),
                        UniformConditional(CBlock("pop = pop && !(graph.node_data[node] == INF)"), uniform_only = True),

                        #CBlock(["if(graph.node_data[node] == INF) continue"]),

                        ClosureHint(ForAll("edge", G.edges("node"),
                               [
                                CDecl([("index_type", "dst", "= graph.getAbsDestination(edge)"),
                                       ("edge_data_type", "wt", "= graph.getAbsWeight(edge)")]), 
                                If("graph.node_data[dst] > graph.node_data[node] + wt",
                                   [CBlock("atomicMin(graph.node_data + dst, graph.node_data[node] + wt)"),
                                    WL.push("dst"),
                                    ]
                                   )
                                ]
                               ))
                        ]
                       ),
                ]),
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [Invoke("sssp_init", ("gg",'0')),
                CDecl(("int", "i", "= 0")),
                ClosureHint(Iterate("while", "wl", "sssp_kernel", ['gg'],
                                    worklist_init = WLInit("gg.nedges*2", [0]),
                                    stmts = [CBlock(["i++"])], 
                                    extra_cond=('&&', 'i < gg.nnodes'),
                                ),
                        ),
                CBlock('printf("iterations: %d\\n", i)')
                ])
        ])

