# -*- mode: python -*-

from gg.ast import *
from gg.ast.params import *

import cgen

ast = Module([
        Kernel("kernel", [LockArrayParam("test_lock")],
               [Atomic("test_lock", "0",
                       [CBlock(["printf(\"acquire lock\\n\")"])],
                       [CBlock(["printf(\"failed to acquire lock\\n\")"])],
                       )]
               ),
        Kernel("main", [], [
                CDecl([("dim3", "blocks", "(1,1,1)"),
                       ("dim3", "threads", "(2,1,1)")]),
                CDecl(("LockArray", "locks", "(2)")),
                Invoke("kernel", ["locks"]),
                CBlock(["cudaDeviceSynchronize()"])                
                ], 
               host=True, ret_type="int"),

        ])

