from gg.ast import *
from gg.lib.graph import Graph

G = Graph("graph")

# Adam Polak's algorithm

ast = Module([
        CBlock([cgen.Include("kernels/segmentedsort.cuh"),
                ]),
        CBlock(["void debug_output(CSRGraphTy &g, unsigned int *valid_edges);"], parse=False),
        Kernel("preprocess", [G.param(), ('unsigned int *', 'valid_edges')], 
               [CDecl(('const index_type', 'last', ' = graph.nnodes')),
                ForAll("node", G.nodes(), 
                       [CDecl([('bool', 'pop', ''),
                               ('int', 'degree', '')]),
                        Assign('pop', G.valid_node("node")),
                        If("pop", [CBlock('degree = graph.getOutDegree(node)')]),
                        ClosureHint(ForAll("edge", G.edges("node"), 
                                           [CDecl([('index_type', 'dst', '= graph.getAbsDestination(edge)'),
                                                   ('int', 'dst_degree', '= graph.getOutDegree(dst)'),
                                                   ]),
                                            If('(dst_degree > degree) || (dst_degree == degree && dst > node)',
                                               [CBlock(["graph.edge_data[edge] = dst",
                                                        "atomicAdd(valid_edges + node, 1)"])
                                                ],
                                               [CBlock(["graph.edge_data[edge] = graph.nnodes" ])],
                                               )
                                            ]
                                           )
                                    )
                        ]
                       ),
                ]
               ),
        Kernel("intersect", [G.param(), ('index_type', 'u'), ('index_type', 'v'), ('unsigned int *', 'valid_edges')],
               [
                CDecl([('index_type', 'u_start', '= graph.getFirstEdge(u)'),
                       ('index_type', 'u_end', '= u_start + valid_edges[u]'),
                       ('index_type', 'v_start', '= graph.getFirstEdge(v)'),
                       ('index_type', 'v_end', '= v_start + valid_edges[v]'),
                       ('int', 'count', '= 0'),
                       ('index_type', 'u_it', '= u_start'),
                       ('index_type', 'v_it', '= v_start'),
                       ('index_type', 'a', ''),
                       ('index_type', 'b', ''),                       
                       ]),
                While('u_it < u_end && v_it < v_end',
                      [
                        CBlock('a = graph.getAbsDestination(u_it)'),
                        CBlock('b = graph.getAbsDestination(v_it)'),                        
                        CDecl(('int', 'd', '= a - b')),
                        If('d <= 0', [CBlock('u_it++')]),
                        If('d >= 0', [CBlock('v_it++')]),
                        If('d == 0', [CBlock('count++')]),
                        ]
                      ),                      
                CBlock('return count'),
                ],
               device=True,
               ret_type = 'unsigned int',
               ),
        Kernel("count_triangles", [G.param(), ('unsigned int *', 'valid_edges'), ('int *', 'count')], 
               [CDecl(('int', 'lcount', '=0')),
                ForAll("v", G.nodes(), 
                       [CDecl([('bool', 'pop', ''),
                               ('int', 'd_v', '')]),
                        Assign('pop', G.valid_node("v")),
                 
                        ClosureHint(ForAll("edge", G.edges("v", limit='valid_edges[v]'), 
                                           [CDecl([('index_type', 'u', '= graph.getAbsDestination(edge)'),
                                                   ('index_type', 'd_u', '= graph.getOutDegree(u)'),
                                                   ('int', 'xcount', '= 0')]),
                                            #CBlock('printf("%d -> %d\\n", v, u)'),
                                            CBlock('xcount = intersect(graph, u, v, valid_edges)'),
                                            If('xcount', [CBlock("atomicAdd(count, xcount)")])
                                            ]
                                           )
                                    ),
                        ]
                       ),
                #CBlock("atomicAdd(count, lcount)")
                ],
               ),
        Kernel("gg_main", [('CSRGraphTy&', 'hg'), ('CSRGraphTy&', 'gg')],
               [CDecl([('Shared<int>', 'count', '(1)'),
                       ('Shared<unsigned int>', 'valid_edges', '(hg.nnodes)')]),
                CBlock("count.zero_gpu()"),
                CBlock("valid_edges.zero_gpu()"),
                Invoke("preprocess", ['gg', 'valid_edges.gpu_wr_ptr()']),
                CBlock("mgpu::SegSortPairsFromIndices(gg.edge_data, gg.edge_dst, gg.nedges, (const int *) gg.row_start + 1, gg.nnodes - 1, *mgc);", parse=False),
                #CBlock("mgpu::SegSortKeysFromIndices(gg.edge_dst, gg.nedges, (const int *) gg.row_start + 1, gg.nnodes - 1, *mgc);", parse=False),
                #CBlock('gg.copy_to_cpu(hg)'),
                #CBlock('debug_output(hg, valid_edges.cpu_rd_ptr())'),
                #CBlock("exit(0)"),
                Invoke("count_triangles", ['gg', 'valid_edges.gpu_rd_ptr()', 'count.gpu_wr_ptr()']),
                CBlock('printf("triangles: %d\\n", *count.cpu_rd_ptr())')
                ]
               ),
        ])
