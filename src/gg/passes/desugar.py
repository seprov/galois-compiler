import gg.ast.walkers
import gg.ast.modifier
import gg.ast
import gg.passes
import gg.lib.wl
import gg.lib.rv
import logging

logger = logging.getLogger(__name__)

class DesugaredAnno(gg.ast.ASTNodeAnno):
    desugared = None
    clonable = True

    def __init__(self, desugared = True):
        self.desugared = desugared

    def clone(self):
        return self._clone_helper(DesugaredAnno(self.desugared))

class KernelParamsAnno(gg.ast.ASTNodeAnno):
    params = None
    clonable = False

    def clone(self):
        return self._clone_helper(KernelParamsAnno())

class KernelParams(gg.ast.walkers.ASTWalker):
    def visit_Kernel(self, node):
        if not node.check_gen(self.gen):
            return

        params = []

        if node.contains_wl:
            params.append(gg.ast.params.WLParam("wl"))

        if node.contains_exclusive:
            params.append(gg.ast.params.ExclusiveLocksParam("_ex"))
            
        if node.contains_barrier and node.barrier_level == 0:
            params.append(gg.ast.params.GlobalBarrierParam("gb"))

        if node.contains_rfpf:
            # do not yet support All
            assert "ALL" not in node.call_contexts, node.call_contexts
            params.append(gg.ast.params.RetValParam("ret_val"))

        node.anno.kernel_params = KernelParamsAnno(params = params)

        logger.debug("Kernel '%s' has desugared params '%s'" % (node.name, ",".join([str(s) for s in node.anno.kernel_params.params])))
        #print node.name, node.anno.kernel_params.params

class RFPFLowering(gg.ast.modifier.ASTModifier):
    def visit_ReturnFromParallelFor(self, node):
        if not node.check_gen(self.gen):
            return node

        if node.has_anno('desugared'):
            return node

        self.nodes_generated = True
        node.anno.desugared = DesugaredAnno()
        return [gg.lib.rv.RV("ret_val").return_(node.value), node]

class ReXLowering(gg.ast.modifier.ASTModifier):
    def visit_Retry(self, node):
        if not node.check_gen(self.gen):
            return node

        if node.has_anno('desugared'):
            return node
        #self.cur_block.add_stmt("re_wl.push(%s)" % (node.args))

        self.nodes_generated = True
        node.anno.desugared = DesugaredAnno()
        self.compiler.log.debug('Desugaring %s' % (node,))

        if hasattr(node, 'merge') and node.merge:
            return [gg.lib.wl.Worklist("out").push(node.args), node]
        else:
            return [gg.lib.wl.Worklist("retry").push(node.args), node]
        
class DesugaringPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail', 'KernelPropsPass'])
    
    def run(self, compiler, unit, gen, pm):
        w = KernelParams()
        w.visit3(compiler, unit.ast, gen)

        r = RFPFLowering()
        r.nodes_generated = False
        r.visit3(compiler, unit, unit.ast, gen)
        if r.nodes_generated: pm.set_nodes_generated()

        r = ReXLowering()
        r.nodes_generated = False
        r.visit3(compiler, unit, unit.ast, gen)
        if r.nodes_generated: pm.set_nodes_generated()

        return True
