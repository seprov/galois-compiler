import gg.ast
import gg.ast.walkers
import gg.ast.anno
from gg.ast.utils import Stack

import gg.passes

class NamedParent(gg.ast.walkers.ASTPreOrderWalker):
    def generic_node_exit(self, node):
        if len(self.path) and self.path.top is node:
            self.path.pop()
            
    def generic_node_visitor(self, node):
        if len(self.path): # no gen check since parent might have changed?
            gg.ast.anno.NamedParent(node, number = self.path.top.number)

        if hasattr(node, "name") and node.name is not None:
            assert node.number not in self.linear
            self.linear[node.number] = node

            self.path.push(node)
            
        return True

    def set_named_parents(self, node, gen):
        self.path = Stack()
        self.linear = {}
        self.gen = gen
        self.visit(node)


class NamedParentBuilderPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail'])
    rdepends = set(['PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):
        v = NamedParent()
        v.set_named_parents(unit.ast, gen)
        unit.named_parents = v.linear

        return True
        
