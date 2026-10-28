# -*- mode: python -*-

from gg.ast import *
from gg.ast.anno import Uniform, Unroll
from gg.lib.graph import Graph
from gg.lib.wl import Worklist
from gg.ast.params import GraphParam
from gg.backend.cuda.anno import LaunchBounds
import cgen

WL = Worklist()
G = Graph("graph")

ast = Module([
        CBlock(["typedef int edge_data_type", 
                "typedef int node_data_type",
                cgen.Define("RESIDENCY", 6),
                ]),
        CDeclGlobal(("extern const node_data_type", "INF", "= INT_MAX")),
        Kernel("kernel", [G.param(), ('int', 'src')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["graph.node_data[node] = INF "]),
                        # If("node == src", 
                        #    [ForAll("edge", G.edges("node"),
                        #            [WL.push("edge")]),
                        #     ])
                        ]
                       )
                ]
               ),
        LaunchBounds(Kernel("contract_expand", [G.param(), ('int', 'LEVEL')],
                            [CDecl([("const int","WHTSIZE","= 64"), ("__shared__ volatile int", "whash[__kernel_tb_size/32][WHTSIZE]", "")]),
                             Uniform(ForAll("wlnode", WL.items(),
                                            [
                                CDecl([("int", "node", ""),
                                       ("bool", "pop", "")]),
                                WL.pop("pop", "wlnode", "node"),
                                If("pop", [
                                        CBlock("pop = false"),
                                        If("graph.node_data[node] == INF",
                                           [CBlock(["graph.node_data[node] = LEVEL",
                                                    "pop = true"]),
                                            ]),
                                        ]),
                                If("pop", [
                                        CDecl([("const int", "warpid", "= threadIdx.x / 32"),
                                               ("const int", "htentry", "= node & (WHTSIZE - 1)")]),
                                        CBlock("whash[warpid][htentry] = node"),
                                        If("whash[warpid][htentry] == node",
                                           [CBlock(["whash[warpid][htentry] = threadIdx.x",
                                                    "pop = whash[warpid][htentry] == threadIdx.x"])
                                            ]),
                                        ]),
                                LocalBarrier().sync(),
                                UniformConditional(If("!pop", [CBlock("continue")]), uniform_only = False, _only_if_np = True),
                                ForAll("edge", G.edges("node"),
                                       [CDecl(("index_type", "dst", "")),
                                        CBlock(["dst = graph.getAbsDestination(edge)"]),
                                        WL.push("dst"),
                                    ]
                                   ),
                                ])
                                     )
                             ]),
                     max_threads = 'TB_SIZE',
                     min_blocks = 'RESIDENCY'),
        Kernel("gg_main", [GraphParam('hg', True), GraphParam('gg', True)], 
               [GlobalBarrier().setup("contract_expand"),
                CDecl(("int", "LEVEL", "= 0")),
                ClosureHint(Pipe([
                            Invoke("kernel", ("gg", '0')),
                            Unroll(Pipe([
                                        Invoke("contract_expand", ('gg', 'LEVEL')),
                                        CBlock(["LEVEL++"]),
                                        ],
                                        ),
                                   count=4,
                                   ),
                            ], 
                             once=True, wlinit=WLInit("gg.nedges > 65536 ? gg.nedges : 65536", [0]),
                             ),
                        )
                ])
        ])
