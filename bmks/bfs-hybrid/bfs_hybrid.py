# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.ast.params import GraphParam
from gg.parser import Import
from gg.backend.cuda.anno import LaunchBounds

import cgen

WL = Worklist()
G = Graph("graph")

bfs_cx_ast = Import('../bfs-cx/bfs_cx.py')
bfs_tp_ast = Import('../bfs-tp/bfs_tp.py')

ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                cgen.Define("RESIDENCY", 6),
                cgen.Define("TB_SIZE_CX", 128),
                cgen.Define("WORKLISTSIZE", "14336*2")
                ]),
        CDeclGlobal(("extern const node_data_type", "INF", "= INT_MAX")),
        Kernel("kernel", [G.param(), ('int', 'src')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["graph.node_data[node] = INF "])]
                       )
                ]
               ),

        LaunchBounds(bfs_cx_ast.get_kernel("contract_expand"), max_threads ="TB_SIZE_CX", min_blocks= "RESIDENCY"),
        bfs_tp_ast.get_kernel("expand"),
        bfs_tp_ast.get_kernel("contract"),
        bfs_tp_ast.get_kernel("filter"),

#         Kernel("expand", [G.param()],
#                [ForAll("wlnode", WL.items(), 
#                        [CDecl([("int", "node", ""),
#                                ("bool", "pop", "")]),
#                         WL.pop("pop", "wlnode", "node"), 
#                         ForAll("edge", G.edges("node"),
#                                [                                
#                                 CDecl(("index_type", "dst", "")),
#                                 CBlock(["dst = graph.getAbsDestination(edge)"]),
#                                 WL.push("dst"),
# #                                WL.push("edge",_coop_only=True)
#                                 ]
#                                )
#                         ]
#                        ),
#                 #GlobalBarrier().sync()
#                 ]
#                ),
#         Kernel("contract", [G.param(), ('int', 'LEVEL')],
#                [ForAll("wlnode", WL.items(),
#                        [
#                         CDecl([("int", "node", ""),
#                                ("bool", "pop", "")]),
#                         WL.pop("pop", "wlnode", "node"),
#                         If("pop", [
#                                 If("graph.node_data[node] == INF",
#                                    [CBlock(["graph.node_data[node] = LEVEL"]),
#                                     WL.push("node"),
#                                     ]),
#                                 ]),
#                         WL.push("node",_coop_only=True)
#                         ]
#                        )
#                 ]
#                ),                       
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [CDecl(("ApproxBitsetByte", "visited", "(hg.nnodes)")),
                Invoke("kernel", ("gg", '0')),
                CDecl(("int", "LEVEL", "= 0")),
                Pipe([
                    ClosureHint(Unroll(Pipe([
                                        Invoke("contract_expand", ('gg', 'LEVEL')),
                                        CBlock(["LEVEL++"]),
                                        If("pipe.in_wl().nitems() > WORKLISTSIZE", [CBlock("break")])
                                        ], name="cx_pipe"
                                            ), count=4)),
                    Pipe([
                        Invoke("contract", ('gg', 'LEVEL')),
                        Invoke("expand", ('gg',)), 
                        Invoke("filter", ('visited',)), 
                        CBlock(["LEVEL++"]),
                        #WL.print_size("LEVEL")
                    ], name = "cx_tp_pipe"),
                ],
                     wlinit=WLInit("gg.nedges > 65536 ? gg.nedges : 65536", [0]),
                     name = "main_pipe"
                 ),
            ])
])
