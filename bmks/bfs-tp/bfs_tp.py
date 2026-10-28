# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.ast.params import GraphParam
from gg.backend.cuda.anno import LaunchBounds

import cgen

WL = Worklist()
G = Graph("graph")

ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                ]),
        CDeclGlobal(("extern const node_data_type", "INF", "= INT_MAX")),
        Kernel("kernel", [G.param(), ('int', 'src')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["graph.node_data[node] = INF "])]
                       )
                ]
               ),

        LaunchBounds(Kernel("expand", [G.param()],
                            [ForAll("wlnode", WL.items(), 
                                    [CDecl([("int", "node", ""),
                                            ("bool", "pop", "")]),
                                     WL.pop("pop", "wlnode", "node"), 
                                     ForAll("edge", G.edges("node"),
                                            [                                
                                    CDecl(("index_type", "dst", "")),
                                    CBlock(["dst = graph.getAbsDestination(edge)"]),
                                    WL.push("dst"),
                                    #                                WL.push("edge",_coop_only=True)
                                    ]
                                            )
                                     ]
                                    ),
                             #GlobalBarrier().sync()
                             ]
                            ),
                     max_threads = 'TB_SIZE',
                     min_blocks = 8),        
        LaunchBounds(Kernel("contract", [G.param(), ('int', 'LEVEL')],
                            [ForAll("wlnode", WL.items(),
                                    [
                            CDecl([("int", "node", ""),
                                   ("bool", "pop", "")]),
                            WL.pop("pop", "wlnode", "node"),
                            If("pop", [
                                    If("graph.node_data[node] == INF",
                                       [CBlock(["graph.node_data[node] = LEVEL"]),
                                        WL.push("node"),
                                        ]),
                                    ]),
                            WL.push("node",_coop_only=True)
                            ]
                                    )
                             ]),
                     max_threads = 'TB_SIZE',
                     min_blocks = 8),
        LaunchBounds(Kernel("filter", [('ApproxBitsetByte', 'visited')],
                            [ForAll("wlnode", WL.items(),
                                    [
                            CDecl([("int", "node", ""),
                                   ("bool", "pop", "")]),
                            WL.pop("pop", "wlnode", "node"),
                            If("pop", [
                                    If("!visited.is_set(node)",
                                       [CBlock("visited.set(node)"),
                                        WL.push("node"),]),
                                    ]),
                            WL.push("node",_coop_only=True)
                            ]
                                    )
                             ]),max_threads = 'TB_SIZE',
                     min_blocks = 8),       
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [GlobalBarrier().setup("expand"),
                Invoke("kernel", ("gg",'0')),
                CDecl(("int", "LEVEL", "= 0")),
                CDecl(("ApproxBitsetByte", "visited", "(hg.nnodes)")),
                ClosureHint(Pipe([
                            Invoke("contract", ('gg', 'LEVEL')),
                            Invoke("expand", ('gg',)), 
                            Invoke("filter", ('visited',)), 
                            CBlock(["LEVEL++"]),
                            ],
                             wlinit=WLInit("gg.nedges > 65536 ? gg.nedges : 65536", [0]),
                             ),
                        )
                ])
        ])
