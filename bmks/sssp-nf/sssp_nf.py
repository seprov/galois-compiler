# -*- mode: python -*-

from gg.ast import *
from gg.ast.params import GraphParam
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.backend.cuda.anno import LaunchBounds
import cgen

G = Graph("graph")
WL = Worklist()

ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                "typedef int * gint_p", # gpu int ptr
                ]),
        CDeclGlobal(("extern const node_data_type", "INF", "= INT_MAX")),
        CDeclGlobal(("extern int", "DELTA", "")),        
        Kernel("kernel", [G.param(), ('int', 'src')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["graph.node_data[node] = (node == src) ? 0 : INF "])]
                       )
                ]
               ),
       Kernel("remove_dups", [('int *', 'marks')],
               [ForAll("wlnode", WL.items(),
                       [CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode", "node"),
                        CBlock("marks[node] = wlnode")
                        ]
                       ),
                GlobalBarrier().sync(),
                ForAll("wlnode2", WL.items(),
                       [CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode2", "node"),
                        If("marks[node] == wlnode2", [WL.push("node")])
                        ]
                       )
                ]
               ),
        LaunchBounds(Kernel("sssp_kernel", [G.param(), ('int', 'delta')],
                            [ForAll("wlnode", WL.items(),                        
                                    [CDecl([("int", "node", ""),
                                            ("bool", "pop", "")]),
                                     WL.pop("pop", "wlnode", "node"),

                                     UniformConditional(If("pop && graph.node_data[node] == INF", [CBlock("continue")]), uniform_only = False),
                                     UniformConditional(CBlock("pop = pop && !(graph.node_data[node] == INF)"), uniform_only = True),

                                     ClosureHint(ForAll("edge", G.edges("node"),
                                                        [
                                        CDecl([("index_type", "dst", "= graph.getAbsDestination(edge)"),
                                               ("edge_data_type", "wt", "= graph.getAbsWeight(edge)")]), 
                                        If("graph.node_data[dst] > graph.node_data[node] + wt",
                                           [CBlock("atomicMin(graph.node_data + dst, graph.node_data[node] + wt)"),
                                            If("graph.node_data[node] + wt <= delta",
                                               [Respawn("dst")],
                                               [Disable(WL.push("dst"), "parcomb")],
                                               )
                                            ]
                                           )
                                        ]
                                                        ),
                                                 _ignore = False,
                                                 )
                                     ]
                                    ),
                             ]),
                     max_threads = "TB_SIZE", min_blocks = "2",
                     ),
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [CDecl(("Shared<int>", "level", "(hg.nnodes)")),
                CBlock("level.cpu_wr_ptr()"),
                #CDecl('Timer t("remove_dups")'),
                GlobalBarrier().setup("remove_dups"),
                CDecl(('gint_p', 'glevel', '')),
                Invoke("kernel", ("gg",'0')),
                CDecl([("int", "i", "= 0"), ("int", "curdelta", "= 0")]),
                CBlock('printf("delta: %d\\n", DELTA)'),
                CBlock('glevel = level.gpu_wr_ptr()'),
                ClosureHint(Pipe([Invoke("sssp_kernel", ['gg', 'curdelta']),
                                  #WL.print_size("i"),
                                  #CBlock("t.start()"),
                                  ArrayInfo(Invoke("remove_dups", ['glevel']),
                                            ainfo = {'glevel': ArrayVarInfo('glevel', 'level.size()')}),
                                  #CBlock("t.stop()"),
                                  #WL.print_size("i"),
                                  CBlock(["i++", "curdelta += DELTA"])], 
                                 wlinit = WLInit("gg.nedges*2", [0]),
                             ),
                        ),
                #CBlock('printf("time in remove_dups: %llu\\n", t.total_duration())'),
                CBlock('printf("iterations: %d\\n", i)')
                ])
        ])

