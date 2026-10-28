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
        Kernel("outer_not_uniform", [G.param(), ('int', 'LEVEL')],
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
                               ]
                           )]
                   )]),

        Kernel("outer_uniform", [G.param(), ('int', 'LEVEL')],
               [Uniform(ForAll("wlnode", WL.items(), 
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
                                       ]),
                                   ])
                    )]),

    Kernel("inner_uniform", [G.param(), ('int', 'LEVEL')],
           [ForAll("wlnode", WL.items(), 
                   [CDecl([("int", "node", ""),
                           ("bool", "pop", "")]),
                    WL.pop("pop", "wlnode", "node"), 
                        Uniform(ForAll("edge", G.edges("node"),
                               [                                
                                CDecl(("index_type", "dst", "")),
                                CBlock(["dst = graph.getAbsDestination(edge)"]),
                                If("graph.node_data[dst] == INF",
                                   [CBlock(["graph.node_data[dst] = LEVEL"]),
                                    WL.push("dst")], []),
                                ]
                                   ))]
                    )]),

        Kernel("both_uniform", [G.param(), ('int', 'LEVEL')],
               [Uniform(ForAll("wlnode", WL.items(), 
                       [CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode", "node"), 
                        Uniform(ForAll("edge", G.edges("node"),
                               [                                
                                CDecl(("index_type", "dst", "")),
                                CBlock(["dst = graph.getAbsDestination(edge)"]),
                                If("graph.node_data[dst] == INF",
                                   [CBlock(["graph.node_data[dst] = LEVEL"]),
                                    WL.push("dst")], []),
                               ]
                                   ))]
                           ))]),
           
             
])
