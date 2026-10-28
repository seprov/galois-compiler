# -*- mode: python -*-

from gg.ast import *
from gg.lib.graph import Graph

import cgen

G = Graph("graph")

ast = Module([
        Kernel("kernel2", [('CSRGraph', 'graph'), ('int', 'LEVEL')],
               [ForAll("node", G.nodes(), 
                       [CBlock(["index_type dst"]),]
                       ),
                ]),
        ])
