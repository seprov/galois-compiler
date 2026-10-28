from gg.ast import *
from gg.ast.params import *
from gg.types import *

ast = Module([Kernel("test_atomic", [LockArrayParam('locks'),
                                     ("int *", "y"),
                                     ("int *", "x"),
                                     ("int", "limit")],
                     [If("tid < limit", 
                        [CBlock('printf("hello\\n")'),
                         Atomic("locks", "x[tid]",
                                [CBlock(["y[x[tid]] += 1"])],
                                []
                            )
                         ]
                        )]
                     ),
             Kernel("main", [], 
                    [CDecl(("int", "THREADS", "=64")),
                     CDecl([("Shared<int>", "y", "(THREADS)"),
                            ("Shared<int>", "x", "(THREADS)"),
                            ("int *", "z", "")]),
                     CDecl([("dim3", "blocks", "(1)"),
                            ("dim3", "threads", "(THREADS)")]),
                     CDecl(("LockArray", "locks", "(THREADS)")),
                     CBlock(["y.zero_gpu()",
                             "x.zero_gpu()",
                             ]),
                     Invoke("test_atomic", ["locks", "y.gpu_wr_ptr()", "x.gpu_rd_ptr()", "THREADS"]),
                     CBlock("check_cuda(cudaDeviceSynchronize())"),
                     CBlock(["z = y.cpu_rd_ptr()"]),
                     For("i", RangeIterator("THREADS"),
                         [CBlock('printf("%d %d\\n", i, z[i])')]
                         )
                     ],
                    host=True,
                    ret_type = "int"),
                    ])
                     
