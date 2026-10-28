from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist

G = Graph("graph")
WL = Worklist()

ast = Module([
        CBlock([cgen.Include("curand.h")]),
        CBlock([cgen.Define("UNMARKED", "0"),
                cgen.Define("MARKED", "1"),
                cgen.Define("NON_INDEPENDENT", "2"),
                cgen.Define("NON_MAXIMAL", "3"),
                cgen.Define("SEED1", "0x12345678LL"),
                cgen.Define("SEED2", "0xabbdef12LL"),
                cgen.Define("SEED3", "0xcafe1234LL"),
                cgen.Define("SEED4", "0x09832516LL"),
                ]),
        Kernel("gen_prio_gpu", [G.param(), ("unsigned int *", "prio"), 
                                ('unsigned int', 'x'), ('unsigned int', 'y'),
                                ('unsigned int', 'z'), ('unsigned int', 'w')],
               [
                CBlock(["x ^= tid",
                        "y ^= tid",
                        "z ^= tid",
                        "w ^= tid",
                        "assert(!(x == 0 && y == 0 && z == 0 && w == 0))"]),               
                ForAll("node", G.nodes(), [
                        CDecl(('unsigned int', 't', '')),
                        CBlock(["t = x ^ (x << 11)",
                                "x = y", # this assumes values last beyond log thread, so this is not an IrGL function!
                                "y = z",
                                "z = w",
                                "w = w ^ (w >> 19) ^ t ^ (t >> 8)",
                                "prio[node] = w",
                                ])
                        ])
                ]),
        Kernel("gen_prio", [G.param(), ("unsigned int *", "prio")],
               [Names(["CURAND_STATUS_SUCCESS", "CURAND_RNG_PSEUDO_DEFAULT", "CURAND_ORDERING_PSEUDO_SEEDED", 
                       "CURAND_RNG_PSEUDO_MT19937", "CURAND_ORDERING_PSEUDO_BEST"]),
                CDecl([("curandGenerator_t", "gen", "")]),
                CBlock(["check_rv(curandCreateGenerator(&gen, CURAND_RNG_PSEUDO_MT19937), CURAND_STATUS_SUCCESS)",
                        "check_rv(curandSetPseudoRandomGeneratorSeed(gen, SEED1), CURAND_STATUS_SUCCESS)",
                        "check_rv(curandSetGeneratorOrdering (gen, CURAND_ORDERING_PSEUDO_BEST), CURAND_STATUS_SUCCESS)",
                        #"check_rv(curandGenerate(gen, prio, graph.nnodes), CURAND_STATUS_SUCCESS)",
                        ]),
                ],
               host = True),               
        Kernel("init_wl", [G.param()], 
               [
                ForAll("node", G.nodes(), 
                       [
                        WL.push("node")
                        ]
                       )
                ]
               ),
        Kernel("mark_nodes", [G.param(), ("const unsigned int * __restrict__", "prio")],
               [
                ForAll("wlnode", WL.items(), 
                       [
                        CDecl([("bool", "pop", ""), 
                               ("int", "node", ""),
                               ]),
                        
                        WL.pop("pop", "wlnode", "node"),

                        CDecl([("int", "max_prio", "= prio[node]"),
                               ("int", "max_prio_node", "= node")]),

                        ForAll("edge", G.edges("node"), # not ForAll
                               [
                                CDecl(("index_type", "dst", "= graph.getAbsDestination(edge)")),
                                If("dst != node && graph.node_data[dst] != NON_INDEPENDENT && prio[dst] >= max_prio", 
                                   [If("(prio[dst] > max_prio) || dst > max_prio_node",
                                       [CBlock(["max_prio = prio[dst]",
                                               "max_prio_node = dst"
                                                ]),
                                        ]
                                       )
                                    ],
                                   ),
                                ],
                               ),
                        #CBlock('printf("%d %d %d\\n", tid, node, max_prio_node)'),
                        If("max_prio_node == node", 
                           [CBlock(["assert(graph.node_data[node] == UNMARKED)", 
                                    "graph.node_data[node] = MARKED"]
                                   )
                            ]
                           )
                        ]
                       )
                ]
               ),
        
        Kernel("drop_marked_nodes_and_nbors", [G.param()],
               [
                ForAll("wlnode", WL.items(), 
                       [
                        CDecl([("bool", "pop", ""), 
                               ("int", "node", ""),
                               ]),
                        
                        WL.pop("pop", "wlnode", "node"),

                        CDecl(("bool", "drop", "= false")),

                        If("graph.node_data[node] == MARKED", [CBlock("drop = true")]),

                        If("!drop",
                           [
                                ForAll("edge", G.edges("node"), # ForAll
                                       [
                                        CDecl(("index_type", "dst", "= graph.getAbsDestination(edge)")),
                                        If("graph.node_data[dst] == MARKED", [CBlock("drop = true")]) # TODO: break
                                        ]
                                       )
                                ]
                           ),
                        
                        If("!drop", [WL.push("node")], 
                           [If("graph.node_data[node] == UNMARKED", 
                               [CBlock("graph.node_data[node] = NON_INDEPENDENT")]
                               )
                            ]
                           )
                        ]
                       )
                ]
               ),
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
                ClosureHint(Pipe([
                            Invoke("init_wl", ['gg']),
                            Pipe([
                                    Invoke("mark_nodes", ['gg', 'prio.gpu_rd_ptr()']),
                                    Invoke("drop_marked_nodes_and_nbors", ['gg']),
                                    CBlock("STEPS++"), 
                                    # If("LEVEL > 3", [CBlock("break")]),
                                    ], 
                                 ),
                            ],
                                 wlinit=WLInit("gg.nnodes", []), once=True)
                            ),
                CBlock('printf("Total steps: %d\\n", STEPS)'),
                ]),
        
        
        ])
        
