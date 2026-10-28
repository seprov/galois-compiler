# -*- mode: python -*-

import sys
sys.path.append("../src")

from gg.ast import *
from gg.lib.graph import Graph

import cgen
import inspect

G = Graph("graph")

def get_line_no():
    x = inspect.stack()
    omost_lineno = x[-1][2]
    del x
    return omost_lineno


class ModuleX(Module):
    def __init__(self, stmts):
        super(ModuleX, self).__init__(stmts)
        self.line_no = get_line_no()

ast = ModuleX([
        Kernel("kernel2", [('CSRGraph', 'graph'), ('int', 'LEVEL')], [ForAll("node", G.nodes(), [CBlock(["index_type dst"]),]),]),
        ])

print ast.line_no
