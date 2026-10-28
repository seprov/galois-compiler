from gg.ast import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.types import RangeIterator

# IrGL-ized version of Soman's conn.cu
# https://github.com/jyosoman/GpuConnectedComponents/blob/master/conn.cu

G = Graph("graph")
WL = Worklist()

def EL(node):
    return LaunchConfig(node, blocks = "edge_blocks")

def NL(node):
    return LaunchConfig(node, blocks = "node_blocks")

ast = Module([
        # initialize, possibly like update_an?
        CDeclGlobal(('extern unsigned long', 'DISCOUNT_TIME_NS', '')),
        Kernel("init", [G.param()], 
               [
                ForAll("node", G.nodes(), [CBlock("graph.node_data[node] = node")])
                ]
               ),
        #CBlock("typedef index_type et", parse=False),
        # no equivalent since this preps the edge list
        Kernel("prep_edge_src", [G.param(), ('index_type *', 'edge_src')],
               [
                ForAll("node", G.nodes(),
                       [
                        CDecl(('bool', 'pop', '')),
                        Assign('pop', G.valid_node("node")),
                        ClosureHint(ForAll("edge", G.edges("node"), [
                                    #CBlock("edge_src[edge] = make_int2(node, graph.getAbsDestination(edge))")
                                    CBlock("edge_src[edge] = node")
                                    ]))
                        ]
                       )
                ]
               ),
        # _Select_winner_init
        Kernel("hook_init", [G.param(), ('index_type *', 'edge_src')],
               [ForAll("edge", RangeIterator("graph.nedges"),
                       [CDecl([('index_type', 'x', '= edge_src[edge]'),
                               ('index_type', 'y', '= graph.getAbsDestination(edge)')]),
                        
                        CDecl([('index_type', 'mx', '= x > y ? x : y'),
                               ('index_type', 'mn', '= x > y ? y : x'),
                               ]),
                        
                        CBlock("graph.node_data[mx] = mn"),
                        ]
                       )
                ]
               ),
        # select_winner2
        Kernel("hook_high_to_low", [G.param(), ('const __restrict__ index_type *', 'edge_src'), ('char *', 'marks')],
               [
                ForAll("edge", RangeIterator("graph.nedges"),
                       [If("!marks[edge]", 
                          [CDecl([('index_type', 'u', '= edge_src[edge]'),
                                  ('index_type', 'v', '= graph.getAbsDestination(edge)')]),
                           CDecl([('node_data_type', 'p_u', '= graph.node_data[u]'),
                                  ('node_data_type', 'p_v', '= graph.node_data[v]'),]),

                           CDecl([('index_type', 'mx', '= p_u > p_v ? p_u : p_v'),
                                  ('index_type', 'mn', '= p_u > p_v ? p_v : p_u'),
                                  ]),
                             
                           If("mx == mn", 
                              [CBlock("marks[edge] = 1")],
                              [CBlock("graph.node_data[mn] = mx"),
                               ReturnFromParallelFor("true")]
                              ),
                           ]
                           )
                        ]
                       ),
                ]
               ),
        # select_winner
        Kernel("hook_low_to_high", [G.param(), ('index_type *', 'edge_src'), ('char *', 'marks')],
               [
                ForAll("edge", RangeIterator("graph.nedges"),
                       [If("!marks[edge]", 
                           [CDecl([('index_type', 'u', '= edge_src[edge]'),
                                   ('index_type', 'v', '= graph.getAbsDestination(edge)')]),
                            CDecl([('node_data_type', 'p_u', '= graph.node_data[u]'),
                                   ('node_data_type', 'p_v', '= graph.node_data[v]'),]),
                            CDecl([('index_type', 'mx', '= p_u > p_v ? p_u : p_v'),
                                   ('index_type', 'mn', '= p_u > p_v ? p_v : p_u'),
                                    ]),
                            
                            If("mx == mn", 
                               [CBlock("marks[edge] = 1")],
                               [CBlock("graph.node_data[mx] = mn"),
                                 ReturnFromParallelFor("true")]
                               ),
                            ]
                           )
                        ]
                       )
                ]
               ),
        # p_jump
        Kernel("p_jump", [G.param()],
               [
                ForAll("node", G.nodes(), 
                       [
                        CDecl([('node_data_type', 'p_u', '= graph.node_data[node]'),
                               ('node_data_type', 'p_v', '= graph.node_data[p_u]'),]),
                        If("p_u != p_v", 
                           [CBlock("graph.node_data[node] = p_v"),
                            ReturnFromParallelFor("true"),
                            ]
                           )
                        ]
                       )
                ]
               ),
        # update_mask, note we use worklists, not masks
        Kernel("identify_roots", [G.param()], 
               [ForAll("node", G.nodes(),
                       [
                        If("graph.node_data[node] == node", 
                           [WL.push("node")],
                           )
                        ]
                       )
                ]
               ),
        # p_jump_masked, but using a worklist
        Kernel("p_jump_roots", [G.param()],
               [ForAll("wlnode", WL.items(),
                       [
                        CDecl([('bool', 'pop', ''), ('int', 'node', '')]),

                        WL.pop("pop", "wlnode", "node"),

                        CDecl([('node_data_type', 'p_u', '= graph.node_data[node]'),
                               ('node_data_type', 'p_v', '= graph.node_data[p_u]'),]),

                        If("p_u != p_v", 
                           [CBlock("graph.node_data[node] = p_v"),
                            ReturnFromParallelFor("true"),
                            ]
                           )
                        ]
                       )
                ]
               ),
        # p_jump_unmasked, using a worklist
        Kernel("p_jump_leaves", [G.param()], # not exactly the same as _unmasked
               [ForAll("node", G.nodes(),
                       [
                        CDecl([('node_data_type', 'p_u', '= graph.node_data[node]'),
                               ('node_data_type', 'p_v', '= graph.node_data[p_u]'),]),

                        If("p_u != p_v", 
                           [CBlock("graph.node_data[node] = p_v")]
                           )
                        ]
                       )
                ]
               ),
        # same, but this is counted in timing, maybe use ReturnSum
        Kernel("count_components", [G.param(), ('int *', 'count')],
               [
                ForAll("node", G.nodes(), 
                       [
                        If("node == graph.node_data[node]", 
                           [CBlock("atomicAdd(count, 1)")]
                           )
                        ]
                       ),
                ]
               ),              
        Kernel("gg_main", [('CSRGraphTy&', 'hg'), ('CSRGraphTy&', 'gg')], 
               [
                Names(['edge_data_type']),
                CDecl([('int', 'it_hk', '= 1'),]),
                CDecl([('Shared<index_type>', 'edge_src', '(gg.nedges)')]),
                CDecl([('Shared<char>', 'edge_marks', '(gg.nedges)')]),
                CDecl(('bool', 'flag', '= false')),
                CDecl([('int', 'edge_blocks', ''),
                       ('int', 'node_blocks', '')]),

                CBlock(["edge_blocks = hg.nedges / TB_SIZE + 1",
                        "node_blocks = hg.nnodes / TB_SIZE + 1"]),

                #CBlock('check_cuda(cudaMemset(gg.edge_data, 0, gg.nedges * sizeof(edge_data_type)))'),
                CBlock('edge_marks.zero_gpu()'),
                CDecl([('cudaEvent_t', 'start', ''),
                       ('cudaEvent_t', 'stop', '')]),
                CBlock(["check_cuda(cudaEventCreate(&start))",
                        "check_cuda(cudaEventCreate(&stop))"]),  
                CBlock("check_cuda(cudaEventRecord(start))"),
                NL(Invoke("prep_edge_src", ["gg", "edge_src.gpu_wr_ptr()"])),
                CBlock("check_cuda(cudaEventRecord(stop))"),
                NL(Invoke("init", ["gg"])),
                EL(Invoke("hook_init", ["gg", "edge_src.gpu_rd_ptr()"])),
                NL(ClosureHint(Iterate("while", "any", "p_jump", ["gg"]))),
                Pipe([DoWhile("flag",
                              [
                                Invoke("identify_roots", ["gg"]),
                                If("it_hk != 0",
                                   [EL(Invoke("hook_low_to_high", ["gg", "edge_src.gpu_rd_ptr()", 
                                                                   "edge_marks.gpu_wr_ptr()"])),
                                    CBlock("flag = *(retval.cpu_rd_ptr())", parse=False, _scope="cpu"),
                                    CBlock("flag = _rv.local", parse=False, _scope="gpu"),
                                    CBlock(["it_hk = (it_hk + 1) % 4"])],
                                   [EL(Invoke("hook_high_to_low", ["gg", "edge_src.gpu_rd_ptr()",
                                                                   "edge_marks.gpu_wr_ptr()"])),
                                    CBlock("flag = *(retval.cpu_rd_ptr())", parse=False, _scope="cpu"),
                                    CBlock("flag = _rv.local", parse=False, _scope="gpu"),
                                    ]
                                   ),
                                If("!flag", [CBlock("break")]),
                                ClosureHint(Iterate("while", "any", "p_jump_roots", ["gg"])),
                                NL(Invoke("p_jump_leaves", ["gg"])),
                                ], 
                              ),
                      ],
                     wlinit=WLInit("gg.nnodes", []),
                     once=True
                     ),
                CBlock('printf("iterations: %d\\n", it_hk)'),
                CDecl([("Shared<int>", "count", "(1)")]),
                CBlock("*(count.cpu_wr_ptr()) = 0"),
                Invoke("count_components", ['gg', 'count.gpu_wr_ptr()']),
                CBlock('printf("components: %d\\n", *(count.cpu_rd_ptr()))'),
                CDecl(('float', 'ms', '=0')),                
                CBlock(["check_cuda(cudaEventElapsedTime(&ms, start, stop))",
                        "DISCOUNT_TIME_NS = (int) (ms * 1000000)",
                        'printf("prep_edge_src: %llu ns\\n", DISCOUNT_TIME_NS)']),
                ]
               )        
        ])
