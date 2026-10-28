from gg.ast import *
from gg.ast.params import *
from gg.types import *
from gg.lib.wl import Worklist
from gg.backend.cuda.anno import LaunchBounds
import cgen

# cc level - warp, tb
# combine load - 0 - 1.0
# external atomic load (to others) - 0 - 1.0
# external atomic load (spread) - 0 - 1.0     # op vs CAS?
# tb_size, warps per SM

WL = Worklist()

ast = Module([CBlock([cgen.Include('stdlib.h', False)]),
              LaunchBounds(Kernel("test_cc_baseline", [("int *", "will_push"),
                                                       ("int *", "will_atomic_add"),
                                                       ("int *", "atomic_add_base"),
                                                       ],
                                  [
                    ForAll("wlnode", WL.items(), 
                           [
                            If("will_atomic_add[tid] != 0", [CBlock("atomicAdd(atomic_add_base + will_atomic_add[tid], 1)")]),
                            If("will_push[tid]", [Disable(WL.push("tid"), "parcomb")]),
                            ]
                           )
                    ]), max_threads=128, min_blocks=16),

              LaunchBounds(Kernel("test_cc", [("int *", "will_push"),
                                              ("int *", "will_atomic_add"),
                                              ("int *", "atomic_add_base"),
                                              ],
                                  [
                    ForAll("wlnode", WL.items(), 
                           [
                            If("will_atomic_add[tid] != 0", [CBlock("atomicAdd(atomic_add_base + will_atomic_add[tid], 1)")]),
                            If("will_push[tid]", [WL.push("tid")]),
                            ]
                           )
                    ]
                                  ), max_threads=128, min_blocks=16),
              
              Kernel("init_rand_array", [("float", "fraction"),
                                         ("int", "N"),
                                         ("int *", "array")],
                     [CDecl([("long int", "threshold", "= RAND_MAX*fraction"),
                             ("long int", "r", "")]),
                      CBlock(['printf("threshold: %ld, fraction: %f\\n", threshold, fraction)']),
                      For("i", RangeIterator("N"),
                          [CBlock("r = random()"),
                           If("r < threshold", [CBlock("array[i] = 1")]),
                           ])
                      ], host=True),

              Kernel("main", [('int', 'argc'), ('char **', 'argv')], 
                    [CDecl([("int", "TOTAL", "=atoi(argv[1])"),
                            ("int", "THREADS", "=128"),
                            ("int", "pushes", "= atoi(argv[2])"),
                            ("float", "fraction", "=((float) pushes)/TOTAL"),
                            ("int", "wl_size", "= TOTAL"),
                            ]),
                     
                     CDecl([("Shared<int>", "wp", "(TOTAL)"),
                            ("Shared<int>", "wa", "(TOTAL)"),
                            ("Shared<int>", "a", "(TOTAL)"),
                            ("int *", "ah", ""),
                            ("int *", "all_nodes", ""),
                            ]
                           ),
                     CDecl([("dim3", "blocks", "(TOTAL/THREADS)"),
                            ("dim3", "threads", "(THREADS)")]),

                     If("blocks.x > 15*16", [CBlock("blocks.x = 15 * 16")]),
                     
                     CBlock(["wp.zero_gpu()",
                             "wa.zero_gpu()",
                             "a.zero_gpu()",
                             ]),            

                     If("fraction >= 1.0", [CBlock("fraction = 1.0")]),
                     CBlock("all_nodes = (int *) malloc(sizeof(int) * TOTAL)"),
                     CBlock("init_rand_array(fraction, TOTAL, wp.cpu_wr_ptr())"),
                     Block([
                        Pipe([
                                Invoke("test_cc", ["wp.gpu_rd_ptr()", "wa.gpu_rd_ptr()", "a.gpu_wr_ptr()"]),
                                CBlock('printf("%d\\n", pipe.in_wl().nitems())'),
                                ],
                             once=True, wlinit=WLInitFromArray("wl_size+1", "all_nodes", "wl_size")),
                        ]),
                     Block([
                        Pipe([
                                Invoke("test_cc_baseline", ["wp.gpu_rd_ptr()", "wa.gpu_rd_ptr()", "a.gpu_wr_ptr()"]),
                                CBlock('printf("%d\\n", pipe.in_wl().nitems())'),
                                ],
                             once=True, wlinit=WLInitFromArray("wl_size+1", "all_nodes", "wl_size")),
                        ]),
                     CBlock("check_cuda(cudaDeviceSynchronize())"),
                     CBlock(["ah = a.cpu_rd_ptr()"]),
                     # For("i", RangeIterator("TOTAL"),
                     #     [CBlock('printf("%d %d, ", i, ah[i])')]
                     #     )
                     ],
                    host=True,
                    ret_type = "int"),
                    ])
                     
