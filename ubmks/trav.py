# -*- mode: python -*-

from gg.ast import *
from gg.ast.anno import *
from gg.lib.wl import Worklist
from gg.lib.graph import Graph

import cgen

WL = Worklist()
G = Graph("graph")

ast = Module([
        CBlock([cgen.Define("TB_SIZE", 32)]),
        Kernel("kernel2", [G.param()],
               [ForAll("wlnode", WL.items(), 
                       [CDecl([("bool", "pop", ""), ("int", "node", "")]),
                        WL.pop("pop", "wlnode", "node"), 
                        ForAll("edge", G.edges("node"), 
                               [CBlock("atomicAdd(graph.edge_data + edge, 1)")]
                               )
                        ]
                       )
                ,
                ]),
        Kernel("main", [('int', 'argc'), ('char **', 'argv')], 
               [CDecl([("dim3", "blocks", "(1)"), 
                       ("dim3", "threads", "(TB_SIZE)")]),
                GlobalBarrier().setup("kernel2"),
                CDecl([("CSRGraphTy", "g", ""),
                      ("CSRGraphTy", "gg", "")]),
                CBlock(["g.read(argv[1])",
                        'printf("nodes: %d, edges: %d\\n", g.nnodes, g.nedges)',
                        "g.copy_to_gpu(gg)"
                        ]),
                Iterate("while", "wl", "kernel2", ['gg'], 
                        stmts = [CBlock("break")],
                        worklist_init = WLInit("g.nnodes", list(range(1,99))),
                        _sign = [('CSRGraphTy&', 'gg')],
                        _call = ['gg'],
                        ),
                CBlock("gg.copy_to_cpu(g)"),
                CFor(CDecl(("int", "i", "= 0")), "i< g.nedges", "i++", 
                     [If("g.edge_data[i] != 1",
                         [CBlock('printf("%d %d\\n", i, g.edge_data[i])')]
                         )
                      ])                     
                ],
               host=True,ret_type="int")
        ])
