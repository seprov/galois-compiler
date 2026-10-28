from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist

# based on the MIS implementation in Pannotia

G = Graph("graph")
WL = Worklist()

def LC(node):
    return LaunchConfig(node, blocks = "blocks_1t") # , threads = "threads_1t") interferes with threads selection


ast = Module([
        CBlock([cgen.Define("ST_NP", -1),
                cgen.Define("ST_INACTIVE", -2),
                cgen.Define("ST_IND", 2),
                cgen.Define("SEED1", "0x12345678LL"),
                cgen.Define("SEED2", "0xabbdef12LL"),
                cgen.Define("SEED3", "0xcafe1234LL"),
                cgen.Define("SEED4", "0x09832516LL"),
                ]),
        Kernel("gen_prio_gpu", [G.param(),
                                ('unsigned int *', 'prio'),
                                ('unsigned int', 'x'), ('unsigned int', 'y'),
                                ('unsigned int', 'z'), ('unsigned int', 'w')],
               [
                CBlock(["x ^= tid",
                        "y ^= tid",
                        "z ^= tid",
                        "w ^= tid",
                        "assert(!(x == 0 && y == 0 && z == 0 && w == 0))"]),               
                ForAll("node", G.nodes(), [
                        Names(["UINT_MAX"]),
                        CDecl(('unsigned int', 't', '')),
                        CBlock(["t = x ^ (x << 11)",
                                "x = y", # this assumes values last beyond log thread, so this is not an IrGL function!
                                "y = z",
                                "z = w",
                                "w = w ^ (w >> 19) ^ t ^ (t >> 8)",
                                "prio[node] = w",                                
                                ]),
                        If("w == UINT_MAX", [CBlock("prio[node] = UINT_MAX - 1")]),
                        ])
                ]),
        Kernel("init", [G.param(),
                        ("int *", "c_array"), 
                        ("int *", "cu_array"), 
                        ],
               [
                ForAll("node", G.nodes(), [
                        CBlock("c_array[node] = ST_NP"),
                        CBlock("cu_array[node] = ST_NP"),
                        CBlock("graph.node_data[node] = 0")
                        ])
                ]),
        
        Kernel("mis1", [G.param(), 
                        ('unsigned int *', 'prio'),
                        ('int *', 'c_array'),
                        ('unsigned int *', 'min_array'),
                        ],
               [
                ForAll("node", G.nodes(), 
                       [If("c_array[node] == ST_NP",
                           [CDecl(("unsigned int", "minn", "= UINT_MAX")),
                        
                            For("edge", G.edges("node"), [
                                        CDecl(('index_type', 'dst', '=graph.getAbsDestination(edge)')),
                                        If("dst != node && c_array[dst] == ST_NP", 
                                           [If("prio[dst] < minn", 
                                              [CBlock("minn = prio[dst]")]
                                               )
                                            ]),
                                        ]),
                            CBlock("min_array[node] = minn"),
                            ReturnFromParallelFor("true"),
                            ]),
                        ]),
                ]),

        Kernel("mis2", [G.param(), ('unsigned int *', 'prio'),
                        ('int *', 'c_array'),
                        ('int *', 'cu_array'),
                        ('unsigned int *', 'min_array')],
               [
                ForAll("node", G.nodes(),
                       [If("prio[node] < min_array[node] && c_array[node] == ST_NP",
                           [CBlock("graph.node_data[node] = ST_IND"),
                            CBlock("c_array[node] = ST_INACTIVE"),

                            For("edge", G.edges("node"),
                                [CDecl(('index_type', 'dst', '= graph.getAbsDestination(edge)')),
                                 If("c_array[dst] == ST_NP", [CBlock("cu_array[dst] = ST_INACTIVE")])
                                 ]
                                ),
                            ]),
                        ]),
                ]),
        Kernel("mis3", [G.param(), ('int *', 'cu_array'), ('int *', 'c_array')],
               [ForAll("node", G.nodes(),                       
                       [If("cu_array[node] == ST_INACTIVE", [CBlock("c_array[node] = cu_array[node]")])],
                       )]),
        
        Kernel("gg_main", [('CSRGraphTy&', 'hg'), ('CSRGraphTy&', 'gg')],
               [
                CDecl([("Shared<unsigned int>", "prio", "(hg.nnodes)"), ("int", "STEPS", "= 0")]),
                CDecl([("ggc::Timer", "t", '("random")')]),
                CBlock("t.start()"),
                #CBlock(["gen_prio(hg, prio.gpu_wr_ptr())"]),
                Invoke("gen_prio_gpu", ['gg', 'prio.gpu_wr_ptr()', 'SEED1', 'SEED2', 'SEED3', 'SEED4']),
                CBlock("cudaDeviceSynchronize()"),
                CBlock(["t.stop()", 'printf("Random number generation took %llu ns\\n", t.duration())']),
                #CBlock("exit(0)"),
                CDecl([("Shared<int>", "c_array", "(hg.nnodes)"),
                       ("Shared<int>", "cu_array", "(hg.nnodes)"),
                       ("Shared<unsigned int>", "min_array", "(hg.nnodes)"),
                       ]),

                # like CC, mis is also beholden to stalling ...
                
                CDecl([('int', 'threads_1t', ' = 128'),
                       ('int', 'blocks_1t', ' = (hg.nnodes + threads_1t - 1) / threads_1t')]),

                LC(Invoke("init", ['gg', 'c_array.gpu_wr_ptr()', 'cu_array.gpu_wr_ptr()'])),
                LC(Iterate("while", "any", "mis1", ['gg', 'prio.gpu_wr_ptr()', 'c_array.gpu_wr_ptr()', 
                                                 'min_array.gpu_wr_ptr()'],
                        stmts=[
                            LC(Invoke("mis2", ['gg', 'prio.gpu_wr_ptr()', 'c_array.gpu_wr_ptr()', 
                                               'cu_array.gpu_wr_ptr()', 'min_array.gpu_rd_ptr()'])),

                            LC(Invoke("mis3", ['gg', 'cu_array.gpu_rd_ptr()', 'c_array.gpu_wr_ptr()'])),
                        CBlock('STEPS++'),
                        #CBlock('printf("%d ", STEPS)'),
                        ]
                           )),
                CBlock('printf("Total steps: %d\\n", STEPS)'),
                ]),
        
        
        ])
        
