from gg.passes.astmisc import *
from gg.passes.kanno import *
from gg.passes.rwsets import RWSetsPass
from gg.passes.names import NamedParentBuilderPass
from gg.passes.callcfg import CallConfigPass, CallConfigDumperPass

class TUnit(object):
    "Contains AST + additional information useful during compilation"

    def __init__(self, compiler, ast):
        self.ast = ast
        self.node_number = 0
        self.outlined_kernels = set()

        compiler.pm.add_pass([KernelListPass(), CFGBuilderPass(),
                              KernelPropsPass(), 
                              KernelCallContextsPass(),
                              RWSetsPass(), ASTNumberingPass(),
                              NamedParentBuilderPass(),
                              CallConfigPass(), 
                              CallConfigDumperPass()])

    def get_closest_named_node(self, node):
        assert node.has_anno("named_parent")
        return self.named_parents[node.anno.named_parent.number]

    def get_scoped_optimizations(self, node):
        n = node
        while n != self.ast:
            if n.has_anno("scoped_optimizations"):
                return n
            else:
                n = self.get_closest_named_node(n)

        return n

    def get_opt_value(self, opt, node, compiler):
        n = node
        while True:            
            if n.has_anno("scoped_optimizations") and opt in n.anno.scoped_optimizations.specified:
                return n.anno.scoped_optimizations.options.by_name(opt)

            if n is self.ast:
                return compiler.options.by_name(opt)

            n = self.get_scoped_optimizations(self.get_closest_named_node(n))
