# -*- mode: python -*-

from gg.ast import *
from gg.ast.anno import *
from gg.lib.wl import Worklist
from gg.lib.graph import Graph

import cgen

WL = Worklist()
G = Graph("graph")

ast = Module([
        Kernel("test_np", [G.param()],
               [ForAll("wlnode", WL.items(), 
                       [CDecl([("bool", "pop", ""),
                               ("int", "node", "")]),
                        WL.pop("pop", "wlnode", "node"), 
                        ForAll("edge", G.edges("node"), 
                               [CBlock("graph.edge_data[edge] = tid")]
                               )
                        ]
                       )
                ,
                ]),
        Kernel("main", [('int', 'argc'), ('char **', 'argv')], 
               [CDecl([("dim3", "blocks", "(1)"), 
                       ("dim3", "threads", "(TB_SIZE)")]),
                CDecl([("CSRGraphTy", "g", ""),
                      ("CSRGraphTy", "gg", "")]),
                CBlock(["g.read(argv[1])",
                        'printf("nodes: %d, edges: %d\\n", g.nnodes, g.nedges)',
                        ]),
                CFor(CDecl(("int", "i", "= 0")), "i< g.nedges", "i++", 
                     [CBlock('g.edge_data[i] = -1')]
                     ),
                CBlock(["g.copy_to_gpu(gg)"]),
                Iterate("while", "wl", "test_np", ['gg'], 
                        stmts = [CBlock("break")],
                        worklist_init = WLInit("g.nnodes", [0, 1]),
                        _sign = [('CSRGraphTy&', 'gg')],
                        _call = ['gg'],
                        ),
                CBlock("gg.copy_to_cpu(g)"),
                CFor(CDecl(("int", "i", "= 0")), "i< g.nedges", "i++", 
                     [CBlock('printf("%d %d\\n", i, g.edge_data[i])')]
                     ),
                ],
               host=True,ret_type="int")
        ])
