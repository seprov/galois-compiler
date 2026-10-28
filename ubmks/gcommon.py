from gg.ast import *

def kernel_sizing(body = None):
    if body:
        o = Kernel("kernel_sizing", [("CSRGraphTy&", "g"), ("dim3 &", "blocks"), ("dim3 &", "threads")],
                   [CBlock(body)
                    ], host=True)
    else:
        o = Kernel("kernel_sizing", [("CSRGraphTy&", "g"), ("dim3 &", "blocks"), ("dim3 &", "threads")],
                   [CBlock(["blocks.x = 14*8", "threads.x = 256"]),
                    ], host=True)

    return o


main = Kernel("main", [('int', 'argc'), ('char **', 'argv')], 
              [CDecl([("CSRGraphTy", "g", ""),
                      ("CSRGraphTy", "gg", "")]),

               If("argc < 2", [CBlock(['fprintf(stderr, "usage: %s [graph-file]\\n", argv[0])', 
                                       'exit(1)'])]),               
               CBlock(["g.read(argv[1])",
                       'printf("nodes: %d, edges: %d\\n", g.nnodes, g.nedges)',
                       "g.copy_to_gpu(gg)"
                       ]),
               CBlock("gg_main(g, gg)"),
               ],
              host=True,ret_type="int")

