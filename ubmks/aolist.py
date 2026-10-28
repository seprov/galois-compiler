# -*- mode: python -*-

from gg.ast import *
from gg.ast.params import *
from gg.lib.wl import Worklist
from gg.lib.aol import AppendOnlyList
import cgen

WL = Worklist("WL")
L = AppendOnlyList("aol")

ast = Module([
        Kernel("kernel", [L.param()],
               [ForAll("wlnode", WL.items(),
                       [WL.pop("wlnode", "id"),
                        L.push("id")]
                       )
                ]
               ),
        Kernel("main", [('int', 'argc'), ('char*', 'argv[]')],
               [L.declare(64),
                CBlock(["dim3 blocks(1), threads(32)"], False),
                Pipe([Invoke("kernel", ['aol'])],
                     wlinit = WLInit("10", [1, 3, 0, 2]),
                     once=True
                     ),
                L.display(),
                CBlock("return 0")
                ],
               host=True, ret_type="int",
               )
        ])

