# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.ast.params import GraphParam

import cgen

G = Graph("graph")
WL = Worklist()

ast = Module([
        CBlock([cgen.Include("kernels/reduce.cuh", system = False)], parse=False),
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                ]),
        CDecl([("float*","P_CURR", ""), 
               ("float*", "P_NEXT", ""),
               ("extern const float","ALPHA","= 0.85"), 
               ("extern const float", "EPSILON", "= 0.01"),
               ("extern int", "MAX_ITERATIONS", "")
               ]),
        Kernel("init_1", [G.param(), ('float *', 'p_curr'), ('float *', 'residual')],
               [ForAll("node", G.nodes(), 
                       [CDecl(("float","update", "")),
                        CBlock(["p_curr[node] = 1.0 - ALPHA",
                                "update = 1.0/graph.getOutDegree(node)"
                                ]
                               ),
                        ForAll("edge", G.edges("node"), 
                               [
                                CDecl(("index_type","dst","")),
                                CBlock("dst = graph.getAbsDestination(edge)"),
                                CBlock("atomicAdd(residual + dst, update)")
                                ]
                               )
                        ]
                       )
                ]
               ),
        Kernel("init_2", [G.param(), ('float *', 'residual')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["residual[node] *= (1.0 - ALPHA) * ALPHA"])]
                       )
                ]
               ),
        Kernel("pagerank_main", [G.param(), ('float *', 'p_curr'), 
                                 ('float *', 'residual'), 
                                 ('float *', 'p_diff')],
               [ForAll("node", G.nodes(),
                       [CDecl([("int","sdeg",""), 
                               ("float","update", "")]),
                        CDecl(("float","res", "=atomicExch(residual + node, 0)")),
                        #CDecl(("float","res", "= residual[node]")),
                        #CBlock("residual[node] = 0"),
                        CBlock("p_curr[node] += res"),
                        CBlock("p_diff[node] = res"),
                        CBlock(["sdeg = graph.getOutDegree(node)",
                                "update = res * ALPHA / sdeg"]),
                        ForAll("edge", G.edges("node"),
                               [
                                CDecl([("index_type","dst", ""), 
                                       ("float","prev","")]),
                                CBlock(["dst = graph.getAbsDestination(edge)",
                                        "prev = atomicAdd(residual + dst, update)"]),
                                ]
                               ),
                        ]),
                ]),
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [CDecl(("Shared<float>", "p[3]", "= {Shared<float> (hg.nnodes), Shared<float> (hg.nnodes), Shared<float>(hg.nnodes)}")), 
                CDecl(("Shared<float>", "r", "(hg.nnodes)")),
                CDecl(("Shared<int>", "marks", "(hg.nnodes)")),
                CDecl([("int","curr","= 0"), ('int','iter', '= 0'), ('float', 'l1', '= 0')]),
                CBlock(["r.zero_gpu()"]),
                Invoke("init_1", ("gg", "p[0].gpu_wr_ptr()", "r.gpu_wr_ptr()")),
                Invoke("init_2", ("gg", "r.gpu_wr_ptr()")),
                While("true", 
                      [Invoke("pagerank_main", ("gg", "p[0].gpu_wr_ptr()", "r.gpu_wr_ptr()", "p[2].gpu_wr_ptr()")),
                       CBlock(['iter++']),
                       CBlock(["mgpu::Reduce(p[2].gpu_rd_ptr(), hg.nnodes, (float )0.0, mgpu::plus<float>(), (float*)0, &l1, *mgc)"], parse=False),
                       CBlock('printf("%d: %f %d\\n", iter, l1, l1 > EPSILON)'),
                       CBlock('p[2].zero_gpu()'),
                       If('!(l1 > EPSILON) || (iter >= MAX_ITERATIONS)', [CBlock('break')]),
                       ]),
                CBlock(['printf("PR took %d iterations\\n", iter)',
                        "P_CURR = p[0].cpu_rd_ptr()",
                        "P_NEXT = p[0].cpu_rd_ptr()"]) # leaks!
                ]
               ),
               ])
