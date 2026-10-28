# -*- mode: python -*-

from gg.ast import *
from gg.ast.anno import *
from gg.lib.wl import Worklist
from gg.types import RangeIterator

import cgen

WL = Worklist()

ast = Module([
        Kernel("test_ri", [],
               [ForAll("wlnode", WL.items(), 
                       [CDecl([("bool", "pop", ""),
                               ("int", "node", "")]),
                        WL.pop("pop", "wlnode", "node"), 
                        ForAll("i", RangeIterator("node"), 
                               [CBlock('printf("%d %d\\n", tid, i)')
                                ]
                               )
                        ]
                       )
                ,
                ]),
        Kernel("main", [('int', 'argc'), ('char **', 'argv')], 
               [CDecl([("dim3", "blocks", "(1)"), 
                       ("dim3", "threads", "(TB_SIZE)")]),
                Iterate("while", "wl", "test_ri", [], 
                        stmts = [CBlock("break")],
                        worklist_init = WLInit("10", [5]),
                        _sign = [],
                        _call = [],
                        ),
                ],
               host=True,ret_type="int")
        ])
