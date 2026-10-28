# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.ast.params import GraphParam
from gg.backend.cuda.anno import LaunchBounds
import cgen

G = Graph("graph")
WL = Worklist()

ast = Module([
        CBlock([cgen.Include("kernels/reduce.cuh", system = False)], parse=False),
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                "typedef float* gfloat_p",
                ]),
        CDeclGlobal([("float*","P_CURR", ""), 
                     ("float*", "P_NEXT", ""),
                     ("extern const float","ALPHA","= 0.85"), 
                     ("extern const float", "EPSILON", "= 0.01"),
                     ("extern int", "MAX_ITERATIONS", ""),
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
                       [CBlock(["residual[node] *= (1.0 - ALPHA) * ALPHA"]),
                        WL.push("node"),
                        ]
                       )
                ]
               ),
       Kernel("remove_dups", [('int *', 'marks')],
               [ForAll("wlnode", WL.items(),
                       [CDecl([("int", "node", ""), ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode", "node"),
                        CBlock("marks[node] = wlnode")
                        ]
                       ),
                GlobalBarrier().sync(),
                ForAll("wlnode2", WL.items(),
                       [CDecl([("int", "node", ""), ("bool", "pop", "")]),
                        WL.pop("pop", "wlnode2", "node"),
                        If("marks[node] == wlnode2", [WL.push("node")])
                        ]
                       )
                ]
               ),        
        LaunchBounds(Kernel("pagerank_main", [G.param(), ('float *', 'p_curr'), 
                                              ('float *', 'residual'), 
                                              ('float *', 'p_diff')],
                            [ForAll("wlnode", WL.items(),
                                    [CDecl([("int","sdeg",""), 
                                            ("float","update", "")]),

                                     CDecl([("int", "node", ""), ("bool", "pop", "")]),
                                     WL.pop("pop", "wlnode", "node"),

                                     CDecl(("float","res", "")),

                                     If("pop", [CBlock(["res =atomicExch(residual + node, 0)",                                       
                                                        "p_curr[node] += res",
                                                        #CBlock("p_diff[node] = res"),
                                                        "sdeg = graph.getOutDegree(node)",
                                                        "update = res * ALPHA / sdeg"]),
                                                ]),
                                     ClosureHint(ForAll("edge", G.edges("node"),
                                                        [
                                        CDecl([("index_type","dst", ""), 
                                               ("float","prev","")]),
                                        CBlock(["dst = graph.getAbsDestination(edge)",
                                                "prev = atomicAdd(residual + dst, update)"]),
                                        If("prev + update > EPSILON && prev < EPSILON", 
                                           [WL.push("dst")]),
                                        #WL.push("dst"),
                                        ]
                                                        ),
                                                 )
                                     ]),
                             ]),
                     max_threads="TB_SIZE", min_blocks="3"),
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [CDecl(("Shared<float>", "p[3]", "= {Shared<float> (hg.nnodes), Shared<float> (hg.nnodes), Shared<float>(hg.nnodes)}")), 
                CDecl(("Shared<float>", "r", "(hg.nnodes)")),
                CDecl(("Shared<int>", "marks", "(hg.nnodes)")),
                GlobalBarrier().setup("remove_dups"),
                CDecl([("int","curr","= 0"), ('int','iter', '= 0'), ('float', 'l1', '= 0')]),
                CBlock(["r.zero_gpu()"]),
                Invoke("init_1", ("gg", "p[0].gpu_wr_ptr()", "r.gpu_wr_ptr()")),
                CDecl([('gfloat_p', 'p0', '=p[0].gpu_wr_ptr()'),
                       ('gfloat_p', 'p2', '=p[2].gpu_wr_ptr()'),
                       ('gfloat_p', 'rp', '=r.gpu_wr_ptr()')]),
                
                ClosureHint(Pipe([
                            ArrayInfo(Invoke("init_2", ("gg", "rp")), ainfo={'rp': ArrayVarInfo('rp', 'r.size()')}),
                            Pipe([
                                    ArrayInfo(Invoke("pagerank_main", ("gg", "p0", "rp", "p2")),
                                              ainfo={'rp': ArrayVarInfo('rp', 'r.size()'),
                                                     'p0': ArrayVarInfo('p0', 'p[0].size()'),
                                                     'p2': ArrayVarInfo('p2', 'p[2].size()'),
                                                 }),                                              
                                    #Invoke("remove_dups", ("marks.gpu_wr_ptr(true)",)),
                                    CBlock(['iter++']),
                                    #CBlock(["mgpu::Reduce(p[2].gpu_rd_ptr(), hg.nnodes, (float )0.0, mgpu::plus<float>(), (float*)0, &l1, *mgc)"], parse=False),
                                    #CBlock('printf("%f %d\\n", l1, l1 > EPSILON)'),
                                    #CBlock('p[2].zero_gpu()'),
                                    #If('!(l1 > EPSILON)', [CBlock('break')]),
                                    If('iter >= MAX_ITERATIONS', [CBlock('break')]),
                                    ],                             
                                 ),
                            ], once=True, wlinit=WLInit("hg.nedges", []))),
                
                CBlock(['printf("PR took %d iterations\\n", iter)',
                        "P_CURR = p[0].cpu_rd_ptr()",
                        "P_NEXT = p[0].cpu_rd_ptr()"]) # leaks!
                ]
               ),
               ])
