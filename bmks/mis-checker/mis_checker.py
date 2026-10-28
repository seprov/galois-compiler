from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist

G = Graph("graph")
WL = Worklist()

ast = Module([
        CDecl([("extern int", "N_MIS_NODES", ""),
               ("extern int*", "MIS_NODES", "")]),
        CBlock([cgen.Define("UNMARKED", "0"),
                cgen.Define("MARKED", "1"),
                cgen.Define("NON_INDEPENDENT", "2"),
                cgen.Define("NON_MAXIMAL", "3"),
                ]),
        Kernel("init_nodes", [G.param()], 
               [
                ForAll("wlnode", WL.items(), 
                       [
                        CDecl([("bool", "pop", ""), 
                               ("int", "node", "")]),
                        WL.pop("pop", "wlnode", "node"),
                        CBlock(["graph.node_data[node] = MARKED"]),   # host graph initializes others to zero
                        ]
                       )
                ]
               ),
        Kernel("check_independence", [G.param()],
               [
                ForAll("wlnode", WL.items(), 
                       [
                        CDecl([("bool", "pop", ""), 
                               ("int", "node", "")]),
                        
                        WL.pop("pop", "wlnode", "node"),

                        ForAll("edge", G.edges("node"),
                               [
                                CDecl(("index_type", "dst", "= graph.getAbsDestination(edge)")),
                                If("dst != node && graph.node_data[dst] == MARKED", [CBlock("graph.node_data[node] = NON_INDEPENDENT")])
                                ]
                               ),
                        ]
                       )
                ]
               ),
        Kernel("check_maximal", [G.param()],
               [
                ForAll("node", G.nodes(), 
                       [
                        If("graph.node_data[node] == UNMARKED", [   # TODO: continue
                                CDecl(("bool", "marked_neighbour", "= false")),
                                ForAll("edge", G.edges("node"), # TODO: ForAllReduce
                                       [                                        
                                        CDecl(("index_type", "dst", "= graph.getAbsDestination(edge)")),
                                        If("dst != node && graph.node_data[dst] != UNMARKED", [CBlock("marked_neighbour = true")])  # TODO: break
                                        ]
                                       ),
                                If("!marked_neighbour", [CBlock("graph.node_data[node] = NON_MAXIMAL")]),
                                ]
                           )
                        ]
                       )
                ]
               ),
        Kernel("gg_main", [('CSRGraphTy&', 'hg'), ('CSRGraphTy&', 'gg')],
               [
                Pipe([
                        Invoke("init_nodes", ['gg']),
                        Invoke("check_independence", ['gg']),
                        Invoke("check_maximal", ['gg']),
                        ], 
                     wlinit=WLInitFromArray("hg.nnodes", "MIS_NODES", "N_MIS_NODES"), once=True)
                ])                             
        ])

