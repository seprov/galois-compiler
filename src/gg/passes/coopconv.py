import gg.ast.modifier
from gg.ast import Kernel, CBlock, CDecl
from gg.ast.anno import Uniform
from gg.ast.params import PipeParam
from gg.ast.callconfig import convert_to_fixed
import gg.passes
from gg.ast.utils import *
import gg.passes.kanno

BLKSCAN = """
const int TB_SIZE = 256
const int BLKSIZE = TB_SIZE
typedef cub::BlockScan<int, BLKSIZE> BlockScan
"""
BLKSCAN_AST = [CDecl([("const int", "BLKSIZE", "= __kernel_tb_size")]),
               CBlock("typedef cub::BlockScan<int, BLKSIZE> BlockScan", parse=False)]

class CoopXformStrip(gg.ast.modifier.ASTModifier):
    def visit_MethodInvocation(self, node):
        if hasattr(node, '_coop_only') and node._coop_only:
            self.nodes_generated = True
            return []

        return node

class CoopXformSetup(gg.ast.modifier.ASTModifier):
    def visit_Kernel(self, node):
        self.coops = {}
        self.coop_save_counter = 0
        
        super(CoopXformSetup, self).visit_Kernel(node)

        for cid, (s, n) in self.coops.items():
            n._coop_xform = False
            self.compiler.info('No coop-conversion found:%s: %s(%s)' % (node.name,
                                                                        n.method, 
                                                                     cid,))
        
        return node

    def visit_ForAll(self, node):
        self.coops_in_me = []
        super(CoopXformSetup, self).visit_ForAll(node)
        
        if len(self.coops_in_me):
            out = []
            for c in self.coops_in_me:
                cid = c._coop_counter
                cond = "%s_cond" % (cid,)
                args = ["%s_%s" % (cid, i) for i in range(len(c.args))]
                out.append(CDecl(("bool", cond, "= false")))
                out.append(CDecl([("int", s, "") for s in args]))
            
            for s in reversed(out):                    
                node.stmts.stmts.insert(0, s)

            node = Uniform(node) #TODO: Guard, also doesn't work for 2nd level

        self.coops_in_me = []
        return node

    def visit_MethodInvocation(self, node):
        if hasattr(node, '_coop_only'):
            if not node._coop_only:
                cid = ",".join(node.args)
                if cid in self.coops:
                    self.compiler.info('Warning: %s found again!' % (cid,))

                self.coops[cid] = ("save_%d" % (self.coop_save_counter), node)
                node._coop_counter = self.coops[cid][0]
                self.coop_save_counter += 1                
            else:
                cid = ",".join(node.args)
                assert cid in self.coops, cid
                node._coop_counter, pnode = self.coops[cid]
                pnode._coop_xform = True
                node._coop_xform = True
                del self.coops[cid]
                self.coops_in_me.append(node)

        return node

class CoopXform(gg.ast.modifier.ASTModifier):
    def visit_Kernel(self, node):
        self.need_blkscan = False
        
        super(CoopXform, self).visit_Kernel(node)

        if self.need_blkscan:            
            convert_to_fixed(node, self.unit)

            if not node.symtab.lookup('BLKSIZE'):
                for o in reversed(BLKSCAN_AST):
                    node.stmts.stmts.insert(0, o)
                    #TODO: update the symbol table

        self.need_blkscan = False
        return node

    def visit_MethodInvocation(self, node):
        if hasattr(node, '_coop_xform') and node._coop_xform == True:
            cid = node._coop_counter
            cond = "%s_cond" % (cid,)
            args = ["%s_%s" % (cid, i) for i in range(len(node.args))]

            self.nodes_generated = True

            if not node._coop_only:
                out = [CBlock("%s = true" % (cond))]

                for (x, v) in zip(args, node.args):
                    out.append(CBlock("%s = %s" % (x, v)))

                return out
            else:
                assert len(node._coop_method.args) == 0, node._coop_method.args
                self.compiler.info('Coop Converting %s.%s' % (node._coop_method.obj_type,node._coop_method.method))
                node._coop_method.args = [cond] + args
                self.need_blkscan = True
                return Uniform(node._coop_method, uniform = False, place_uniform = True, place_level = 0)

        return node

class CoopXformPass(gg.passes.Pass):
    depends = set(['KernelPropsPass', 'SemCheckedASTAvail'])

    def run(self, compiler, unit, gen, pm):
        v = CoopXformSetup()
        v.visit2(compiler, unit, unit.ast)

        v = CoopXform()
        v.nodes_generated = False
        v.visit2(compiler, unit, unit.ast)
        if v.nodes_generated: pm.set_nodes_generated()

        return True

class CoopXformStripPass(gg.passes.Pass):
    depends = set(['KernelPropsPass', 'SemCheckedASTAvail', 'PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):
        v = CoopXformStrip()
        v.nodes_generated = False
        v.visit2(compiler, unit, unit.ast)
        if v.nodes_generated: pm.set_nodes_generated()

        return True
