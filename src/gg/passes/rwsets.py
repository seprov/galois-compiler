import gg.ast.misc.cblocks as cblocks
import gg.passes

class RWSetsPass(gg.passes.Pass):
    depends = set(['SyntaxCheckerPass'])
    rdepends = set(['PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):
        C = cblocks.CReadWriteSets()
        C.visit3(compiler, unit.ast, gen)
        return True
