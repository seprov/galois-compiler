from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.ast.params import GraphParam
import cgen
import gcommon

WL = Worklist()
G = Graph("graph")

ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                cgen.Define("INF", 10000)]),

        Kernel("count_kernel", [G.param()],
               [ForAll("wlnode", WL.items(),
                       [
                        CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode", "node"),
                        ForAll("edge", G.edges("node"),
                                [CDecl(("index_type", "dst", "")),
                                 CBlock(["dst = graph.getAbsDestination(edge)"]),
                                 WL.push("dst"),
                                 ]
                               ),                         
                        ]
                       ),
                ]),

        gcommon.kernel_sizing(["blocks.x = 1", "threads.x = TB_SIZE"]),

        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [
                Pipe([Invoke("count_kernel", ('gg',)),
                      WL.display_items("0"),
                      ],
                     once=True, wlinit=WLInit("hg.nedges", [0]),
                     )
                ]),

        gcommon.main

        ]) 



