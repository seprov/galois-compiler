import gg.passes
from gg.ast.walkers import *

class LightenKernels(gg.ast.modifier.ASTModifier):
    def visit_Kernel(self, node):
        if not node.check_gen(self.gen):
            return node

        if node.host:
            return node

        if node.device and node.has_anno("original_kernel") and node.anno.original_kernel.name in self.unit.outlined_kernels:
            nn = node.clone()
            nn.name += "_light"
            nn.device = True

            self.nodes_generated = True

            return [nn, node]

        return node

class LightenKernelsPass(gg.passes.Pass):
    depends = set(['IPOutlinerGBPass'])

    def run(self, compiler, unit, gen, pm):
        v = LightenKernels()
        v.nodes_generated = False
        v.visit3(compiler, unit, unit.ast, gen)
        if v.nodes_generated: pm.set_nodes_generated()

        return True
