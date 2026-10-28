# -*- mode: python -*-

from gg.ast import *
from gg.ast.anno import *
from gg.lib.wl import Worklist

import cgen

WL = Worklist()

ast = Module([
        CBlock([cgen.Define("INF", 10000000)]),
        Kernel("kernel2", [],
               [ForAll("wlnode", WL.items(), 
                       [WL.pop("wlnode", "node"), 
                        CBlock('printf("%d\\n", node)'),
                        WL.push("node")
                        ]
                       ),
                ]),
        Kernel("main", [('int', 'argc'), ('char **', 'argv')], 
               [CDecl("dim3 blocks(1), threads(10)"),
                Iterate("while", "wl", "kernel2", [], 
                        stmts = [CBlock("break")],
                        worklist_init = WLInit("10", [1024, 12, 14])
                        )
                ],
               host=True,ret_type="int")
        ])
