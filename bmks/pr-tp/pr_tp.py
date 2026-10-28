# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph
from gg.ast.params import GraphParam

import cgen

G = Graph("graph")

ast = Module([
        CBlock([cgen.Include("kernels/reduce.cuh", system = False)], parse=False),
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type"]),
        CDecl([("float*", "P_CURR", ""),
               ("float*", "P_NEXT", ""),
               ("extern const float", "ALPHA", "= 0.85"),
               ("extern const float", "EPSILON", "= 0.01"),
               ("extern int", "MAX_ITERATIONS", ""),
               ]),
        Kernel("init", [G.param(), ('float *', 'p_curr'), ('float *', 'p_next')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["p_curr[node] = 1.0-ALPHA", #/graph.nnodes",
                                "p_next[node] = 0.0"
                                ]
                               )
                        ]
                       )
                ]
               ),
        Kernel("pagerank_push", [G.param(), ('float *', 'p_curr'), ('float *', 'p_next')],
               [ForAll("node", G.nodes(),                        
                       [CDecl([("int", "sdeg", ""), ("float", "update", "")]),
                        CBlock(["sdeg = graph.getOutDegree(node)",
                                "update = p_curr[node] / sdeg"]),
                        
                        ForAll("edge", G.edges("node"),
                               [
                                CDecl(("index_type", "dst", "")),
                                CBlock("dst = graph.getAbsDestination(edge)"),
                                CBlock("atomicAdd(p_next + dst, update)"),
                                ]
                               )
                        ]
                       ),
                ]),        
        Kernel("pagerank_compute", [G.param(), ('float *', 'p_curr'), ('float *', 'p_next'), ('float *', 'diff')],
               [ForAll("node", G.nodes(),
                       [CBlock(["p_next[node] = ALPHA * p_next[node] + (1.0 - ALPHA) / graph.nnodes",
                                "diff[node] = fabs(p_next[node] - p_curr[node])",
                                #'printf("%d %f %f %f\\n", node, p_next[node], p_curr[node], diff[node])',
                                "p_curr[node] = 0.0",
                                ]),
                        ]
                       ),
                ]),        

        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [CDecl(("Shared<float>", "p[3]", "= {Shared<float> (hg.nnodes), Shared<float> (hg.nnodes), Shared<float>(hg.nnodes)}")), 
                CDecl([("int", "curr", "= 0"), ("float", "l1", "= 0.0"), ('int', "iter", "= 0")]),
                
                Invoke("init", ("gg", "p[0].gpu_wr_ptr()", "p[1].gpu_wr_ptr()")),
                DoWhile("l1 > EPSILON && iter < MAX_ITERATIONS",
                        [Invoke("pagerank_push", ("gg", "p[curr].gpu_wr_ptr()", "p[curr ^ 1].gpu_wr_ptr()")),
                         Invoke("pagerank_compute", ("gg", "p[curr].gpu_wr_ptr()", 
                                            "p[curr ^ 1].gpu_wr_ptr()", "p[2].gpu_wr_ptr(true)")),
                         CBlock(["l1 = 0.0", 'iter++']),
                # CFor("int x = 0", "x < hg.nnodes", "x++",
                #      [CBlock([#'printf("%d %f\\n", x, p[2].cpu_rd_ptr()[x])',
                #               "l1 += p[2].cpu_rd_ptr()[x]"]
                #              )
                #       ]),
                         CBlock(["curr ^= 1",
                                 "mgpu::Reduce(p[2].gpu_rd_ptr(), hg.nnodes, (float )0.0, mgpu::plus<float>(), "
                                 "(float*)0, &l1, *mgc)",
                                 ], parse=False),
                         CBlock(['printf("iteration: %d l1 = %f\\n", iter, l1)']),
                         ]),

                CBlock(['printf("l1 = %f after %d iterations\\n", l1, iter)',
                        "P_CURR = p[curr].cpu_rd_ptr()",
                        "P_NEXT = p[curr ^ 1].cpu_rd_ptr()"]) # leaks!
                ]
               ),
        ]
        )
