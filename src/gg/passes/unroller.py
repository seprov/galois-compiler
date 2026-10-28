import gg.passes
import gg.ast.modifier
import gg.ast.walkers
import gg.ast

class PipeUnroller(gg.ast.modifier.ASTModifierScoped):
    def visit_Pipe(self, node):        
        if not node.check_gen(self.gen):
            return node
    
        node.stmts = super(PipeUnroller, self).visit(node.stmts)

        if node.has_anno('unroll'):
            if not self.kernel.host and not self.kernel.device and self.kernel.has_anno('outline') and self.kernel.anno.outline.outline:
                self.nodes_generated = True
                count = max(node.anno.unroll.count, 2)

                if not node.anno.unroll.unrolled:
                    self.compiler.info("Unrolling pipe in '%s' (%d times)" % (self.kernel.name, count))

                    out = []
                    for i in range(count):
                        for s in node.stmts.stmts:
                            out.append(s.clone())

                    node.stmts = gg.ast.Block(out)
                    node.anno.unroll.unrolled = True

        return node

class UnrollerPass(gg.passes.Pass):
    depends = set(['PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):
        v = PipeUnroller()
        v.nodes_generated = False
        v.visit3(compiler, unit, unit.ast, gen)
        if v.nodes_generated: pm.set_nodes_generated()

        return True
