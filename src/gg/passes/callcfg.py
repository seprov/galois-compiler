import gg.ast
import gg.ast.walkers
import gg.ast.anno
import gg.ast.callconfig
import gg.passes

class CallConfig(gg.ast.walkers.ASTWalker):
    def _get_launch_bounds(self, lb):
        # TODO: handle different arches
        assert None in lb.bounds

        return lb.bounds[None][0]
        
    def visit_Kernel(self, node):
        if not node.check_gen(self.gen):
            return

        if node.host:
            return

        if node.device:
            return

        if not (node.host or node.device) and not node.has_anno("call_config"):
            tb_name = "__tb_" + node.name

            if node.has_anno2("cuda.launch_bounds"):
                size = self._get_launch_bounds(node.anno.cuda.launch_bounds)
                cc = gg.ast.callconfig.ShrinkableBlockTy(tb_name, size)
            elif node.contains_exclusive or (node.contains_barrier and node.barrier_level == 0):
                cc = gg.ast.callconfig.ShrinkableBlockTy(tb_name, None)
            elif node.has_anno("outline") and node.anno.outline.outline:
                cc = gg.ast.callconfig.FixedBlockTy("__tb_one", 1)
            else:
                cc = gg.ast.callconfig.ElasticBlockTy(tb_name, None)

            gg.ast.anno.CallConfig(node, cc)
                

class CallConfigDumper(gg.ast.walkers.ASTWalker):
    def visit_Kernel(self, node):
        if node.has_anno("call_config"):
            self.compiler.log.debug("Call Config %s: block: %s, grid: %s" % (node.name, node.anno.call_config.block, node.anno.call_config.grid))

class CallConfigPass(gg.passes.Pass):
    depends = set(['KernelPropsPass'])
    rdepends = set(['PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):
        v = CallConfig()
        v.visit4(compiler, unit, unit.ast, gen)
        return True
        

class CallConfigDumperPass(gg.passes.Pass):
    depends = set(['PostOutputPass'])

    def run(self, compiler, unit, gen, pm):
        v = CallConfigDumper()
        v.visit4(compiler, unit, unit.ast, gen)
        return True
        


