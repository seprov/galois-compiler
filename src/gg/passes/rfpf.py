import gg.passes
import gg.ast.walkers
import gg.ast

class RFPFScan(gg.ast.walkers.ASTWalker):
    def visit_ReturnFromParallelFor(self, node):
        if node.check_gen(self.gen):
            self.compiler.log.info("ReduceAndReturn found")

class RFPFScanPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail', 'KernelPropsPass'])

    def run(self, compiler, unit, gen, pm):
        v = RFPFScan()
        v.visit3(compiler, unit.ast, gen)

        return True
