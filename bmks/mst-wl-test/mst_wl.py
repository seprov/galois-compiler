from gg.ast import *
from gg.ast.params import *
from gg.ast.anno import *
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.lib.aol import AppendOnlyList
import cgen

WL = Worklist()
G = Graph("graph")
EL = AppendOnlyList("el")
EW = AppendOnlyList("ew")
B = AppendOnlyList("bosses")
B_in = AppendOnlyList("b_in")
B_out = AppendOnlyList("b_out")

ast = Module([
        CBlock([cgen.Include("mst.h",False),                
                cgen.Define("INF", "UINT_MAX"),
                ]),
        CDecl(("const int", "DEBUG", "= 0")),
        EL.declare(),
        Kernel("init_wl", [G.param()],
               [ForAll("node", G.nodes(), 
                       [WL.push("node")]
                       )
                ]
               ),

        # place all nodes with cross-component edges onto worklist
        # also find minimum component edge
        Kernel("find_comp_min_elem", [G.param(), 
                                      ('struct comp_data', 'comp'),
                                      LockArrayParam('complocks', LOCKARRAY_TICKET),
                                      ('ComponentSpace', 'cs'),
                                      ('int', 'level'),
                                      B.param(),
                                      ],
               [CBlock(""),
                ForAll("wlnode", WL.items(), 
                       [CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),                        
                        WL.pop("pop", "wlnode", "node"), 
                        CDecl([("unsigned", "minwt", "= INF"), #TODO set min_wt to comp_min_wt /safely/
                               ("unsigned", "minedge", "= INF"),
                               ("int", "degree", "= graph.getOutDegree(node)"),
                               ("int", "mindstcomp", " = 0"), # DEBUG only
                               ("int", "srccomp", "= cs.find(node)"),
                               ("bool", "isBoss", "= srccomp == node")]),
                        ForAll("edge", G.edges("node"),
                               [
                                CDecl(("int", "edgewt", "= graph.getAbsWeight(edge)")),
                                If("edgewt < minwt", 
                                   [CDecl(("int","dstcomp","= cs.find(graph.getAbsDestination(edge))")),
                                    If("dstcomp != srccomp",
                                       [CBlock(["minwt = edgewt",
                                                "minedge = edge"])],
                                       [])
                                    ],
                                   [])
                                ]
                               ),
                        If("isBoss && degree", [B.push("node")]),
                        If("minwt != INF", 
                           [WL.push("node"),
                            Atomic("complocks", 
                                   "srccomp",
                                   [
                                        If("comp.minwt[srccomp] == 0 || (comp.lvl[srccomp] < level) || (comp.minwt[srccomp] > minwt)",
                                           [CBlock(["comp.minwt[srccomp] = minwt", 
                                                    "comp.lvl[srccomp] = level",
                                                    "comp.minedge[srccomp] = minedge", 
                                                    #"comp.minnode[srccomp] = node",  # WHY???
                                                    #"comp.mindstcomp[srccomp] = mindstcomp"
                                                    ])],
                                           [])
                                        ],
                                   [])
                            ], 
                           [If("isBoss && degree", [WL.push("node")])]),
                        ]) # forall
        ]),
        
        # iterate over all worklist nodes
        # join those nodes that have the minimum cross-component edge
        Kernel("union_components", [G.param(), 
                                    ('ComponentSpace', 'cs'),
                                    ('struct comp_data', 'compdata'),
                                    ('int', 'level'),
                                    EL.param(),
                                    EW.param(),
                                    B_in.param(),
                                    B_out.param(),
                                    ],
               [ForAll("wlnode", B_in.items(),
                       [CDecl([("int", "node", ""),
                               ("bool", "pop", "")]),
                        B_in.pop("pop", "wlnode", "node"),
                        CDecl(("int", "r", "= 0")),
                        CDecl([('int', 'dstcomp', '= -1'),
                               ('int', 'srccomp', '= -1')]),
                        If('pop && compdata.lvl[node] == level', 
                           [CBlock(['srccomp = cs.find(node)',
                                    'dstcomp = cs.find(graph.getAbsDestination(compdata.minedge[node]))',
                                    ])
                            ],
                           []),
                        GlobalBarrier().sync(),
                        If('srccomp != dstcomp',
                           [If('!cs.unify(srccomp, dstcomp)', 
                               [B_out.push("node"), CBlock("r = 1")],
                               [EL.push("compdata.minedge[node]"),
                                EW.push("compdata.minwt[node]")]
                               ),
                            ],
                           [],
                           ),
                        EL.push("compdata.minedge[node]", _coop_only=True),
                        EW.push("compdata.minwt[node]", _coop_only=True),
                        GlobalBarrier().sync(),
                        If("r", [ReturnFromParallelFor('true')])
                        ]
                       ),
                ]),
        
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [
                CDecl(("ComponentSpace", "cs", "(hg.nnodes)")),
                EL.construct("hg.nedges"),
                EW.declare("hg.nedges"),
                CDecl([("AppendOnlyList", "bosses[2]", "= {AppendOnlyList(hg.nnodes), AppendOnlyList(hg.nnodes)}"),
                       ("int", "cur_boss", "= 0")]),
                #B.declare("hg.nnodes"),
                GlobalBarrier().setup("union_components"), # TODO
                CDecl(("struct comp_data", "comp", "")),
                CBlock(["comp.weight.alloc(hg.nnodes)",
                        "comp.edge.alloc(hg.nnodes)",
                        "comp.node.alloc(hg.nnodes)",
                        "comp.level.alloc(hg.nnodes)",
                        "comp.dstcomp.alloc(hg.nnodes)",
                        
                        "comp.lvl = comp.level.zero_gpu()",
                        "comp.minwt = comp.weight.zero_gpu()",
                        "comp.minedge = comp.edge.gpu_wr_ptr()",
                        "comp.minnode = comp.node.gpu_wr_ptr()",
                        "comp.mindstcomp = comp.dstcomp.gpu_wr_ptr()",
                        ]),
                CDecl(("LockArrayTicket", "complocks", "(hg.nnodes)")),
                CDecl([("int", "level", "= 1"), ("int", "mw", "= 0"), ("int", "last_mw", "= 0")]),
                Pipe([
                        Invoke('init_wl',['gg']),
                        Pipe([CBlock(["last_mw = mw"]),
                              Invoke('find_comp_min_elem', ['gg', 'comp', 'complocks', 'cs', 'level', 'bosses[cur_boss]']),
                              #WL.print_size("level"),
                              Iterate('while', 'any', 'union_components', ['gg', 'cs', 'comp', 'level', 'el', 'ew', 
                                                                           'bosses[cur_boss]', 'bosses[cur_boss ^ 1]'], 
                                      stmts=[CBlock(["cur_boss ^= 1", "bosses[cur_boss].reset()"])]),
                              #CBlock('printf("components: %llu\\n", cs.numberOfComponentsHost())'),
                              CBlock(['mw = el.nitems()',
                                      'level++']),
                              If("last_mw == mw", [CBlock(["break"])], []),
                              ])
                        ], WLInit("hg.nnodes"), once=True),
                CDecl([('unsigned long int', 'rweight', '= 0'),
                       ('size_t', 'nmstedges', '')]),
                CBlock(['nmstedges = ew.nitems()',
                        'mgpu::Reduce(ew.list.gpu_rd_ptr(), nmstedges, (long unsigned int)0, mgpu::plus<long unsigned int>(), (long unsigned int*)0, &rweight, *mgc)'], parse=False),
                CBlock(['printf("final mstwt: %llu\\n", rweight)',
                        'printf("total edges: %llu, total components: %llu\\n", nmstedges, cs.numberOfComponentsHost())']),
                ]) # kernel
        ]) # module
