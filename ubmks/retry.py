# -*- mode: python -*-

from gg.ast import *
from gg.ast.params import *
from gg.lib.wl import Worklist
import cgen

WL = Worklist()

ast = Module([
        Kernel("kernel", [LockArrayParam("test_lock")],
               [ForAll("wlnode", WL.items(),
                       [WL.pop("wlnode", "id"),
                        Atomic("test_lock", "id",
                               [CBlock(["printf(\"acquired lock %d\\n\", id)"]),
                                WL.push("id")],
                               [CBlock(["printf(\"failed to acquire lock %d: %d\\n\", wlnode, id)"]),
                                Retry(["id"]),
                                ],
                               )
                        ]
                       )
                ]
               ),
        Kernel("main", [('int', 'argc'), ('char*', 'argv[]')],
               [CBlock(["LockArray locks(10)"], False),
                CBlock(["dim3 blocks(1), threads(32)"], False),
                Pipe([Invoke("kernel", ['locks'])],
                     wlinit = WLInit("10", [1, 3, 0, 2]),
                     once=True
                     ),
                CBlock("return 0")
                ],
               host=True, ret_type="int",
               )
        ])

