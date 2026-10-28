import gg.ast.modifier
from gg.ast import Kernel, CBlock, CDecl, Assign
from gg.ast.anno import Uniform
from gg.ast.params import PipeParam
import gg.passes
from gg.ast.utils import *
import gg.passes.kanno
import gg.dfa.focal, gg.dfa.dom

class CCSetupAnno(gg.ast.ASTNodeAnno):
    clonable = True
    cc_setup = True

    def clone(self):
        return CCSetupAnno()

def CCSetup(node, *args, **kwargs):
    node.anno.cc_setup = CCSetupAnno()
    return node

class ParCombXform(gg.ast.modifier.ASTModifierST):
    def __init__(self):
        super(ParCombXform, self).__init__()
        self.pc_starts = Stack()

    def visit_ForAll(self, node):
        # TODO: replace this with a generic modifier (after, before, etc.)
        self.pc_starts.push([])

        super(ParCombXform, self).visit_ForAll(node)

        if len(self.pc_starts.top):
            method = [x[0] for x in self.pc_starts.top]
            start = [x[1] for x in self.pc_starts.top]

            x = CDecl([(t, n, '') for n, t in start])
            
            flags = {}
            for n, t in start:
                flags[n] = {'is_comb_start': True}
            
            x.set_symbol_flags(flags)

            out = [x] + method + [node]
        else:
            out = node

        self.pc_starts.pop()

        return out

    # def pc_style(self, node):
    #     rng = node.anno.parcomb
    #     # TODO: assumes 0 is +count+
    #     assert rng.combiner_method.args[0] == "+count+"

    #     if not node.anno.count.parent_loop: 
    #         self.compiler.log.info('%s does not have a definite count, not eligible for parcomb' % (node,))
    #         return node
    #     else:
    #         self.compiler.log.info('Applying parcomb to %s in %s' % (node, node.anno.count.parent_loop))

    #     lo = node.anno.count.parent_loop
    #     nv = node.anno.count.parent_loop.ndxvar

    #     if lo.nesting_level == 1:
    #         # TODO: make this more general
    #         rng.combiner_method.args[0] = "({start} < {size}) ? (({size} - 1 - {start})/{increment} + 1) : 0".format(start="tid", 
    #                                                                                                                  size="(" + nv.iterator.size() + ")",  
    #                                                                                                                  increment="nthreads")
    #     else:
    #         rng.combiner_method.args[0] = nv.iterator.size() # this should really be trip count, which involves ndxvar...

    #     self.pc_starts.top.append((Assign('start', rng.combiner_method), 
    #                                ('start', rng.combiner_type)))

    #     nv.gen_pos_var = True
    #     nv.pos_var_is_comb_offset = True
    #     pos_var = nv.pos_var_name

    #     # # TODO: check that _is_comb_offset gets through?
    #     # HACK because node hasn't really changed
    #     x = node.anno.count.parent_loop.symtab.lookup(nv.pos_var_name)
    #     print x
    #     if x is None:
    #         node.anno.count.parent_loop.symtab.add(nv.pos_var_name, nv.var_type,is_comb_offset = True)
            

    #     # TODO: start, pos_var, ...
    #     rng.method.args = ["start + " + nv.pos_var_name] + node.args

    #     self.nodes_generated = True

    #     return rng.method

    def replace_args(self, args, resolve):
        #print args, [resolve.get(a, a) for a in args]
        return [resolve.get(a, a) for a in args]

    def _thread_convert_multiple(self, node):
        rng = node.anno.coopconv
        # TODO: assumes 0 is +count+
        method = rng.setup_methods['thread']
        assert method.args[0] == "+count+"

        self.compiler.log.info('Coopconv applying thread aggregation to %s in %s' % (node, node.anno.count.parent_loop))

        lo = node.anno.count.parent_loop
        nv = node.anno.count.parent_loop.ndxvar

        if lo.nesting_level == 1:
            # TODO: make this more general
            method.args[0] = "({start} < {size}) ? (({size} - 1 - {start})/{increment} + 1) : 0".format(start="tid", 
                                                                                                        size="(" + nv.iterator.size() + ")",  
                                                                                                        increment="nthreads")
        else:
            method.args[0] = nv.iterator.size() # this should really be trip count, which involves ndxvar...

        start_name = "_start_%d" % (node.number,)

        self.pc_starts.top.append((CCSetup(Assign(start_name, method)), 
                                   (start_name, rng.combiner_type)))

        nv.gen_pos_var = True
        nv.pos_var_is_comb_offset = True
        pos_var = nv.pos_var_name

        # # TODO: check that _is_comb_offset gets through?
        # HACK because node hasn't really changed
        x = node.anno.count.parent_loop.symtab.lookup(nv.pos_var_name)
        if x is None:
            # the offset is the same for every variable
            node.anno.count.parent_loop.symtab.add(nv.pos_var_name, nv.var_type,is_comb_offset = True)
        else:
            assert x.comb_offset

        # TODO: start, pos_var, ...
        tm = rng.task_method
        tm.args = self.replace_args(tm.args, {'+start+' : start_name, '+ndx+': nv.pos_var_name}) + node.args

        return tm

    def _warp_convert_one(self, node):
        cc = node.anno.coopconv

        m = cc.setup_methods['warp']
        m.args = self.replace_args(m.args, {'+count+': '1'})

        start_name = "_start_%d" % (node.number,)

        t = cc.task_method
        t.args = self.replace_args(t.args, {'+start+': start_name, '+ndx+': '0'}) + node.args

        return [CDecl((cc.combiner_type, start_name, '')), 
                CCSetup(Assign(start_name, m)), 
                cc.task_method]

    def cc_style(self, node):
        cc = node.anno.coopconv

        if len(cc.setup_methods) == 0:
            # reduction whose value will be read outside
            self.nodes_generated = True
            self.compiler.log.info('Coopconv Reduction convertion %s [%s]' % (node, "%s.%s" % (node.obj_type, node.method)))
            return cc.task_method

        if node.anno.count.parent_loop:
            # has definite count
            self.nodes_generated = True
            return self._thread_convert_multiple(node)
        else:
            if "warp" in cc.setup_methods:
                self.compiler.log.info('Coopconv Warp converting one %s' % (node))
                self.nodes_generated = True
                return self._warp_convert_one(node)

        return node
        
    def visit_MethodInvocation(self, node):
        if node.check_gen(self.gen):
            # if hasattr(node.anno, 'parcomb'):
            #     return self.pc_style(node)
            if hasattr(node.anno, 'coopconv'):
                disabled = self.unit.get_opt_value("cc_disable", node, self.compiler)
                wc = "%s.%s" % (node.obj_type, node.method)

                if wc not in disabled:
                    if not (node.has_anno("disable") and "parcomb" in node.anno.disable.what):
                        # disabled using Disable
                        return self.cc_style(node)
                    else:
                        self.compiler.log.info('Coopconv User-Disabled for %s/%s' % (wc, node))
                else:
                    self.compiler.log.info('Coopconv Disabled for %s/%s' % (wc, node))

        return node

class CoopConvTB(gg.ast.modifier.ASTModifierST):
    def __init__(self):
        super(CoopConvTB, self).__init__()

    def visit_MethodInvocation(self, node):
        if node in self.fc_nodes:
            if node.has_anno("coopconv"):
                #print "FC NODE!", node
                pass
            else:
                #print "NO FC NODE", node
                pass

        return node

    def visit_Assign(self, node):
        if node in self.fc_nodes:
            if node.rhs.has_anno("coopconv"):
                #print "FC NODE!", node.rhs
                pass
            else:
                #print "NO FC NODE", node.rhs
                pass

        return node

    def visit_Kernel(self, node):
        #print node.name
        for c in self.unit.cb.cfgs:
            if c.astnode == node:
                z = gg.dfa.dom.PostDominators(c)
                z.analyze()

                y = gg.dfa.focal.FocalPoints(c)
                y.analyze(z)
                fc = y.get_focal_points()
                self.fc = fc
                self.all_nodes = y.all_nodes()
                self.fc_nodes = set()

                for n in self.all_nodes:
                    if n.node_id in self.fc.values:
                        self.fc_nodes.add(n.astnode)

                x = super(CoopConvTB, self).visit_Kernel(node)

                self.fc = None
                self.fc_nodes = None
                return x


        assert False


class ParCombXformPass(gg.passes.Pass):
    depends = set(['CounterPass', 'ASTNumberingPass'])

    def run(self, compiler, unit, gen, pm):
        v = ParCombXform()
        v.nodes_generated = False
        v.visit3(compiler, unit, unit.ast, gen)
        if v.nodes_generated: pm.set_nodes_generated()

        return True


class CoopConvTBPass(gg.passes.Pass):
    depends = set(['ParCombXformPass'])

    def run(self, compiler, unit, gen, pm):
        v = CoopConvTB()
        v.nodes_generated = False
        v.visit3(compiler, unit, unit.ast, gen)
        if v.nodes_generated: pm.set_nodes_generated()

        return True
