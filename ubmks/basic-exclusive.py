# -*- mode: python -*-

from gg.ast import *

import cgen

ast = Module([
        Kernel("kernel", [("Mesh", "mesh")],
               [CDecl([("int", "nc", ""),
                       ("int", "cavity[20]", ""),
                       ("int", "bc", ""),
                       ("int", "boundary[20]", "")]),
                If("tid == 1", 
                   [CBlock(["nc = 1",
                            "bc = 1",
                            "cavity[0] = 1",
                            "boundary[0] = 1",
                            ])
                    ],
                   [CBlock(["nc = 1",
                            "bc = 1",
                            "cavity[0] = 2",
                            "boundary[0] = 1",
                            ])]
                   ),

                If("tid > 2", [CBlock("return")]),

                Exclusive([("mesh", 
                            (("nc", "cavity"), 
                             ("bc", "boundary"))
                            )],
                          [CBlock(["printf(\"%d in exclusive lock\\n\", tid)"])],
                       [CBlock(["printf(\"%d failed to be exclusive\\n\", tid)"])],
                       )]
               ),

        Kernel("main", [], [
                CDecl([("dim3", "blocks",  "(1,1,1)"), 
                       ("dim3", "threads", "(2,1,1)")]),
                
                GlobalBarrier().setup("kernel"),
                Exclusive.setup("2", "kernel"),
                Invoke("kernel", [])], host=True, ret_type="int")
        ])

