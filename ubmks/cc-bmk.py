# -*- mode: python -*-

from gg.ast import *
from gg.ast.anno import *
from gg.lib.wl import Worklist
from gg.lib.graph import Graph

import cgen

WL = Worklist()

# this was used to derive the initial version of cc-bmk.cu, but that
# was heavily modified, so don't use this!

ast = Module([
        Kernel("kernel2", [],
               [ForAll("wlnode", WL.items(), 
                       [CDecl([('int', 'node', ''),
                               ('bool', 'pop', '')]),
                        WL.pop("pop", "wlnode", "node"),
                        WL.push("node"),
                        WL.push("node", _coop_only=True)
                        ]
                       )
                ,
                ]),
        Kernel("main", [('int', 'argc'), ('char **', 'argv')], 
               [CDecl([("dim3", "blocks", "(14*8)"), 
                       ("dim3", "threads", "(256)")]),
                CDecl([('int', 'push', '=atoi(argv[1])')]),
                CDecl(("Timer", "t", '("kernel")')),
                CBlock("t.start()"),
                Iterate("while", "wl", "kernel2", [], 
                        stmts = [CBlock("break")],
                        worklist_init = WLInit("push", [])),
                CBlock(["cudaDeviceSynchronize()",
                        "t.stop()",
                        'printf("time: %llu\\n", t.duration())',
                        ]
                       ),
                ],
               host=True,ret_type="int")
        ])
